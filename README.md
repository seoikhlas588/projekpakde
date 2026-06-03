# ProjekPakde — Auto Update Blocklist Database

Automatic updater for Indonesian blocked domains database using PostgreSQL + Railway Cron.

## Features

* Auto download latest blocklist
* Auto decompress `.csv.zst`
* Auto import to PostgreSQL
* Auto deduplicate domains
* Atomic table swap
* Automatic update via Railway Cron
* Optimized for large datasets (9M+ domains)

---

## Stack

* Python 3.11
* PostgreSQL
* Railway
* psycopg2
* zstandard

---

## Installation

Clone repository:

```bash
git clone https://github.com/seoikhlas588/projekpakde.git
cd projekpakde
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Required:

```env
DATABASE_URL=postgresql://postgres:password@host:5432/railway
```

---

## Railway Setup

### 1. Create PostgreSQL service

Create PostgreSQL service on Railway.

### 2. Create Python service

Deploy this repository to Railway.

### 3. Add DATABASE_URL

Go to:

```text
Service → Variables
```

Add:

```env
DATABASE_URL=your_postgresql_url
```

---

## Cron Schedule

Recommended:

```cron
0 5,17 * * *
```

Runs automatically at:

* 12:00 WIB
* 00:00 WIB

---

## Database Structure

```sql
CREATE TABLE blocklist_domains (
    domain VARCHAR(253) PRIMARY KEY
);
```

---

## Manual Run

```bash
python update_blocklist.py
```

---

## Current Dataset

* 9M+ domains
* Daily updated
* Source: blocklist mirror

---

## License

MIT
