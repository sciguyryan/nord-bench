"""Versioned, atomic benchmark report output with no VPN credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

SCHEMA_VERSION = 1


def write_report(path: Path, report: dict) -> None:
    """Atomically replace a report only after complete JSON serialisation."""
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=".benchmark-report-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
