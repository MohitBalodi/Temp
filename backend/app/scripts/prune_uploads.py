"""Delete verifier uploads whose retention has passed.

    docker compose exec api python -m app.scripts.prune_uploads
    docker compose exec api python -m app.scripts.prune_uploads --dry-run

Retention is `UPLOAD_RETENTION_DAYS` (default 7), set when the file is stored.
Only rows in `uploads` are considered, so issued certificate PDFs are out of
reach by construction even though they sit under the same volume.

Orphan files — written just before a crash, so never committed — are reported
and, unless --dry-run, removed too: nothing in the database refers to them.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Upload
from app.services import uploads

logger = logging.getLogger("prune_uploads")

# A file is only an orphan once it is older than this. `store()` writes the
# file before committing the row, so a file written by a request still in
# flight would otherwise look unreferenced and be deleted under it.
ORPHAN_GRACE = timedelta(hours=1)


def _orphan_files(known: set[str], now: datetime) -> list[str]:
    """Files under the upload root that no row points at and that are not
    recent enough to belong to a request still in flight."""
    root = uploads.upload_root()
    if not root.exists():
        return []
    cutoff = (now - ORPHAN_GRACE).timestamp()
    return [
        str(p)
        for p in sorted(root.iterdir())
        if p.is_file() and str(p) not in known and p.stat().st_mtime < cutoff
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would be deleted, delete nothing."
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    now = datetime.now(UTC)
    db = SessionLocal()
    try:
        due = list(db.scalars(select(Upload).where(Upload.expires_at <= now)))
        all_paths = {p for p in db.scalars(select(Upload.path))}
        orphans = _orphan_files(all_paths, now)

        if args.dry_run:
            logger.info("Would delete %d expired upload(s):", len(due))
            for row in due:
                logger.info("  %s  expired %s  %s", row.id, row.expires_at.isoformat(), row.path)
            logger.info("Would delete %d orphan file(s):", len(orphans))
            for path in orphans:
                logger.info("  %s", path)
            return 0

        rows, files = uploads.prune_expired(db, now=now)
        db.commit()

        removed_orphans = 0
        for path in orphans:
            try:
                Path(path).unlink()
                removed_orphans += 1
            except FileNotFoundError:
                pass

        logger.info(
            "Deleted %d expired upload(s), %d file(s), %d orphan file(s).",
            rows,
            files,
            removed_orphans,
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
