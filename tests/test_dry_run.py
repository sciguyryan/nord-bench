"""Dry-run must never invoke NordVPN connection or disconnection commands."""

import io
import unittest
from unittest.mock import patch

import nordvpn_connection as connection
from nordvpn_benchmark import main


class DryRunTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"server": "uk715.nordvpn.com", "received": 3}]

    @patch.object(connection.sys, "platform", "linux")
    @patch.object(connection.shutil, "which", return_value="/usr/bin/nordvpn")
    def test_disconnected_preview_only_reads_status(self, _which):
        output = io.StringIO()
        with patch.object(connection, "run_client", return_value=self.result("Status: Disconnected\n")) as run:
            self.assertTrue(connection.preview_connection(self.rows, 1, stream=output))
        self.assertEqual([call.args[0] for call in run.call_args_list], ["status"])
        self.assertIn("nordvpn connect uk715", output.getvalue())

    @patch.object(connection.sys, "platform", "linux")
    @patch.object(connection.shutil, "which", return_value="/usr/bin/nordvpn")
    def test_existing_connection_requires_authorisation(self, _which):
        with patch.object(
            connection, "run_client", return_value=self.result("Status: Connected\nHostname: de123\n")
        ) as run:
            self.assertFalse(connection.preview_connection(self.rows, 1, stream=io.StringIO()))
            self.assertTrue(connection.preview_connection(self.rows, 1, replace_existing=True, stream=io.StringIO()))
        self.assertEqual([call.args[0] for call in run.call_args_list], ["status", "status"])

    @patch.object(connection.sys, "platform", "linux")
    @patch.object(connection.shutil, "which", return_value="/usr/bin/nordvpn")
    def test_unknown_status_fails_closed(self, _which):
        with patch.object(connection, "run_client", return_value=self.result("unrecognised")) as run:
            self.assertFalse(connection.preview_connection(self.rows, 1, stream=io.StringIO()))
        run.assert_called_once()

    def test_invalid_server_does_not_call_client(self):
        with patch.object(connection, "run_client") as run, self.assertRaises(connection.ConnectionError):
            connection.preview_connection([{"server": "invalid", "received": 3}], 1)
        run.assert_not_called()

    def test_cli_requires_auto_connect(self):
        with patch("sys.stderr"), self.assertRaises(SystemExit) as error:
            main(["--download", "--dry-run"])
        self.assertEqual(error.exception.code, 2)

    @staticmethod
    def result(stdout):
        from subprocess import CompletedProcess

        return CompletedProcess(["nordvpn"], 0, stdout, "")
