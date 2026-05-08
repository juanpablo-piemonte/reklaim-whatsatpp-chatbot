"""
Delete checkpoint rows for conversations whose 24h customer window expired
more than 24h ago (i.e. inactive for 48h+).

Run with:
    make cleanup
    # or directly:
    .venv/bin/python scripts/cleanup_checkpoints.py [--dry-run]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def main(dry_run: bool = False) -> None:
    import pymysql

    from app.core.config import settings

    if not all([settings.db_host, settings.db_user, settings.db_pass, settings.db_name]):
        print("ERROR: DB credentials not configured. Check your .env file.")
        sys.exit(1)

    ssl = {"ca": settings.db_ssl_cert} if os.path.exists(settings.db_ssl_cert) else None
    conn = pymysql.connect(
        host=settings.db_host,
        user=settings.db_user,
        password=settings.db_pass,
        database=settings.db_name,
        ssl=ssl,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )

    # Threads inactive for 48h+ (window expired >24h ago).
    inactive_threads_sql = """
        SELECT from_phone FROM conversations
        WHERE customer_window_expires_at < NOW() - INTERVAL 24 HOUR
    """

    with conn.cursor() as cur:
        cur.execute(inactive_threads_sql)
        threads = [row["from_phone"] for row in cur.fetchall()]

    if not threads:
        print("No inactive threads found. Nothing to clean up.")
        conn.close()
        return

    print(f"Found {len(threads)} inactive thread(s).")

    placeholders = ", ".join(["%s"] * len(threads))

    counts = {}
    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE thread_id IN ({placeholders})", threads)
            counts[table] = cur.fetchone()["n"]

    print(f"  checkpoints:       {counts['checkpoints']} row(s)")
    print(f"  checkpoint_blobs:  {counts['checkpoint_blobs']} row(s)")
    print(f"  checkpoint_writes: {counts['checkpoint_writes']} row(s)")

    if dry_run:
        print("\nDry run — no rows deleted.")
        conn.close()
        return

    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {table} WHERE thread_id IN ({placeholders})", threads)
        print(f"  Deleted {counts[table]} row(s) from {table}.")

    print("\nDone.")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting.")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
