# Migrating PostgreSQL data to SQLite

FundamenTracker can copy the current PostgreSQL dataset into the SQLite backend
without modifying the source database. This is intended for migrations to a
single-host lightweight deployment such as Raspberry Pi.

## Safety properties

The migration tool:

- opens a PostgreSQL `REPEATABLE READ READ ONLY` transaction so all tables come
  from one consistent snapshot;
- streams source rows in bounded batches rather than loading the whole database
  into memory;
- builds the destination in a temporary SQLite file;
- verifies row counts for every copied table before publishing the destination;
- refuses to overwrite an existing destination unless `--replace-existing` is
  given;
- when replacement is explicitly requested, preserves the previous destination
  as a timestamped backup before the atomic rename.

It never issues PostgreSQL writes.

## Usage

From a checkout with the backend dependencies installed:

```bash
export DATABASE_URL='postgresql://...'
export SQLITE_PATH='/srv/fundamentracker/fundamentracker.db'
python scripts/migrate-postgres-to-sqlite.py
```

You can also pass the values explicitly:

```bash
python scripts/migrate-postgres-to-sqlite.py \
  --database-url 'postgresql://...' \
  --sqlite-path ./fundamentracker.db
```

For a deliberate replacement of an existing SQLite destination:

```bash
python scripts/migrate-postgres-to-sqlite.py \
  --database-url 'postgresql://...' \
  --sqlite-path ./fundamentracker.db \
  --replace-existing
```

Do not replace a SQLite database while a FundamenTracker process is actively
using that file. Stop the target API first, run the migration, and start it only
after migration verification succeeds.

## Copied tables

The copy order preserves foreign-key dependencies:

1. `tickers`
2. `tags`
3. `ticker_tags`
4. `alerts`
5. `alert_history`
6. `signals`
7. `scan_settings`
8. `data_providers`
9. `metric_snapshots`
10. `provider_health`

UUIDs are preserved as text, timestamps and dates as ISO-8601 text, booleans as
SQLite integers, numeric values as SQLite reals, and PostgreSQL JSON/JSONB
objects as JSON text. Repository reads decode the JSON fields back to Python
objects.

## Cut-over rule

Do not point the public API hostname at the SQLite deployment immediately after
the first copy. First validate the API locally against the migrated database.
At final cut-over, stop writes/scans on the old PostgreSQL instance and perform a
fresh migration so the SQLite file contains the final production state.
