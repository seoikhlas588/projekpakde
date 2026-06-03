import os
import re
import sys
import requests
import zstandard as zstd
import psycopg2
from playwright.sync_api import sync_playwright

SOURCE_PAGE = "https://blocklist.skiddle.id/"
DB_URL = os.environ["DATABASE_URL"]

def find_latest_url():
    print("Opening page with browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SOURCE_PAGE, wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#versions-table tbody tr", timeout=60000)

        html = page.content()
        browser.close()

    match = re.search(
        r'href="(https://blocklist\.skiddle\.id/blocklist/versions/\d{8}-[a-f0-9]{16}\.csv\.zst)"',
        html
    )

    if not match:
        raise Exception("Failed to find download URL from rendered page")

    url = match.group(1)

    print(f"Download URL: {url}")

    return url

def download_file(url):
    print(f"Downloading: {url}")

    r = requests.get(url, stream=True, timeout=180)
    r.raise_for_status()

    with open("latest.csv.zst", "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

def decompress_file():
    print("Decompressing...")

    dctx = zstd.ZstdDecompressor()

    with open("latest.csv.zst", "rb") as src, open("latest.csv", "wb") as dst:
        dctx.copy_stream(src, dst)

def update_database():
    print("Connecting to database...")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        cur = conn.cursor()

        print("Preparing staging table...")
        cur.execute("DROP TABLE IF EXISTS blocklist_domains_staging;")
        cur.execute("""
            CREATE TABLE blocklist_domains_staging (
                domain VARCHAR(253)
            );
        """)
        conn.commit()

        print("Importing CSV...")
        with open("latest.csv", "r", encoding="utf-8", errors="ignore") as f:
            cur.copy_expert(
                "COPY blocklist_domains_staging(domain) FROM STDIN WITH (FORMAT csv)",
                f
            )
        conn.commit()

        print("Creating clean table...")
        cur.execute("DROP TABLE IF EXISTS blocklist_domains_new;")
        cur.execute("""
            CREATE TABLE blocklist_domains_new AS
            SELECT DISTINCT LOWER(TRIM(domain)) AS domain
            FROM blocklist_domains_staging
            WHERE domain IS NOT NULL
              AND TRIM(domain) <> '';
        """)
        conn.commit()

        print("Adding primary key...")
        cur.execute("""
            ALTER TABLE blocklist_domains_new
            ADD PRIMARY KEY(domain);
        """)
        conn.commit()

        print("Swapping tables...")
        cur.execute("BEGIN;")
        cur.execute("DROP TABLE IF EXISTS blocklist_domains_old;")
        cur.execute("ALTER TABLE blocklist_domains RENAME TO blocklist_domains_old;")
        cur.execute("ALTER TABLE blocklist_domains_new RENAME TO blocklist_domains;")
        cur.execute("DROP TABLE blocklist_domains_old;")
        cur.execute("DROP TABLE blocklist_domains_staging;")
        cur.execute("COMMIT;")

        cur.execute("SELECT COUNT(*) FROM blocklist_domains;")
        total = cur.fetchone()[0]

        print(f"Update complete. Total domains: {total}")

    except Exception as e:
        conn.rollback()
        print("Update failed:", e)
        sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    latest_url = find_latest_url()
    download_file(latest_url)
    decompress_file()
    update_database()
