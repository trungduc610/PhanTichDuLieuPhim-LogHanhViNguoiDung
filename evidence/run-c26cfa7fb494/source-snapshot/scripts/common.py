"""Shared standard-library helpers; run CLI scripts from the project root."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp must include timezone, e.g. +07:00 or Z')
    return dt.astimezone(timezone.utc)
