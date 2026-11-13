"""SHA-256 helpers. Pure functions, no state.

Used for the issued-PDF hash stored in `certificates.file_sha256` and, later,
for the file-hash check on uploaded documents (Tier 2).
"""

import hashlib
from pathlib import Path

CHUNK_BYTES = 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    """Lowercase hex SHA-256 of `data`."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str, *, chunk_bytes: int = CHUNK_BYTES) -> str:
    """Lowercase hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk_bytes):
            digest.update(block)
    return digest.hexdigest()
