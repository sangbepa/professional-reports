from __future__ import annotations
import contextlib
import fcntl
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class ContractError(ValueError):
    pass


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def hash_data(data):
    return hashlib.sha256(canonical(data).encode()).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def immutable_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        f.write(canonical(data) + "\n")
        f.flush()
        os.fsync(f.fileno())


def now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ContractError("Expected ISO timestamp with timezone") from exc
    if dt.tzinfo is None:
        raise ContractError("Timestamp must include timezone")
    return dt


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ContractError(f"Unsafe identifier: {value!r}")
    return value


def within(root, relative):
    root = Path(root).resolve()
    p = (root / relative).resolve()
    if Path(relative).is_absolute() or not p.is_relative_to(root):
        raise ContractError(f"Path escapes root: {relative}")
    return p


def members(root):
    root = Path(root).resolve()
    result = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(x in {"__pycache__", ".git", ".DS_Store", ".validation", ".pytest_cache", "node_modules"} for x in rel.parts) or p.suffix == ".pyc":
            continue
        if p.is_symlink():
            raise ContractError(f"Release cannot contain symlinks: {rel}")
        if p.is_file():
            result.append({"path": rel.as_posix(), "sha256": digest(p)})
    return result


@contextlib.contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
