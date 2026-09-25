"""Immutable, dated snapshots of every raw source file.

Rule: a snapshot is never overwritten. Each fetch writes
data/snapshots/<source>/<YYYY-MM-DD>/<filename> plus a manifest line. If the
bytes are identical to the most recent snapshot of the same file, no new copy
is written; the manifest records that the existing snapshot was re-confirmed.

Files above MAX_STORED_RAW_BYTES are not committed (the repo would balloon);
their sha256, size and URL are recorded so the exact vintage is identifiable,
and the caller stores the extract it used via `store_extract`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path

from . import config

USER_AGENT = "boomermeter/1.0 (+https://github.com/MalcolmWest2003/boomermeter)"


@dataclass
class Snapshot:
    source: str
    filename: str
    url: str
    sha256: str
    bytes: int
    retrieved: str  # ISO date
    stored_path: str | None  # repo-relative path, or None if too large to store
    content: bytes  # not serialized

    def provenance(self) -> dict:
        d = asdict(self)
        d.pop("content")
        return d


def _manifest(source: str) -> Path:
    return config.SNAPSHOTS / source / "manifest.jsonl"


def _last_entry(source: str, filename: str) -> dict | None:
    path = _manifest(source)
    if not path.exists():
        return None
    last = None
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec["filename"] == filename:
            last = rec
    return last


def http_get(url: str, retries: int = 3, timeout: int = 120) -> bytes:
    err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RuntimeError(f"404 Not Found: {url}") from e
            err = e
        except Exception as e:  # noqa: BLE001 - retried, then re-raised
            err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} tries: {url}: {err}")


def fetch(source: str, filename: str, url: str, retrieved: dt.date | None = None,
          store_raw: bool = True) -> Snapshot:
    content = http_get(url)
    return record(source, filename, url, content, retrieved, store_raw)


def record(source: str, filename: str, url: str, content: bytes,
           retrieved: dt.date | None = None, store_raw: bool = True) -> Snapshot:
    retrieved = retrieved or config.today()
    sha = hashlib.sha256(content).hexdigest()
    last = _last_entry(source, filename)
    stored_path = None
    if last and last["sha256"] == sha:
        stored_path = last.get("stored_path")
        status = "unchanged"
    else:
        status = "new"
        if store_raw and len(content) <= config.MAX_STORED_RAW_BYTES:
            dest = config.SNAPSHOTS / source / retrieved.isoformat() / filename
            if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() != sha:
                raise RuntimeError(f"refusing to overwrite snapshot {dest}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            stored_path = _rel(dest)
    snap = Snapshot(source, filename, url, sha, len(content), retrieved.isoformat(),
                    stored_path, content)
    if status == "new":
        _manifest(source).parent.mkdir(parents=True, exist_ok=True)
        with _manifest(source).open("a") as f:
            f.write(json.dumps({**snap.provenance(), "status": status}) + "\n")
    return snap


def store_extract(snap: Snapshot, name: str, text: str) -> str:
    """Store the subset of a large file the pipeline used, next to its hash."""
    dest = config.SNAPSHOTS / snap.source / "extracts" / f"{snap.sha256[:12]}-{name}"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
    return _rel(dest)


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(config.ROOT))
    except ValueError:
        return str(p)
