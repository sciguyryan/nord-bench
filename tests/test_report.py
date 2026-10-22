"""Regression checks for versioned report writing and CLI safeguards."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nordvpn_report import SCHEMA_VERSION, write_report
from nordvpn_benchmark import main


class ReportTests(unittest.TestCase):
    def test_atomic_report_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            write_report(path, {"schema_version": SCHEMA_VERSION, "measurements": [{"samples_ms": [1.2]}]})
            self.assertEqual(json.loads(path.read_text())["measurements"][0]["samples_ms"], [1.2])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_invalid_payload_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            write_report(path, {"schema_version": SCHEMA_VERSION})
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                write_report(path, {"latency": float("nan")})
            self.assertEqual(path.read_bytes(), original)

    def test_report_must_not_overwrite_results_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "results.json")
            with patch("sys.stderr"), self.assertRaises(SystemExit) as error:
                main(["--download", "--report", path, "--output", path])
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
