import os
import sys
import requests
import psycopg2

DB_URL = os.environ["DATABASE_URL"]
DOWNLOAD_URL = "https://github.com/Skiddle-ID/blocklist/releases/download/latest/domains.txt"

def download_file():
    print(f"Downloading: {DOWNLOAD_URL}")

    r = requests.get(DOWNLOAD_URL, stream=True, timeout=300)
    r.raise_for_status()

    with open("domains.txt", "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

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
                domain TEXT
            );
        """)
        conn.commit()

        print("Importing TXT...")
        with open("domains.txt", "r", encoding="utf-8", errors="ignore") as f:
            cur.copy_expert(
                "COPY blocklist_domains_staging(domain) FROM STDIN",
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
    download_file()
    update_database()
