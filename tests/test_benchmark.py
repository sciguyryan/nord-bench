import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nordvpn_benchmark as b


class BenchmarkTests(unittest.TestCase):
    def test_archive_transport_filtering(self):
        import zipfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(root / "nordvpn.zip", "w") as z:
                z.writestr("ovpn_udp/ae72.nordvpn.com.udp_2.6.ovpn", "proto udp\nremote 127.0.0.1 53\n")
                z.writestr("ovpn_tcp/ae72.nordvpn.com.tcp_2.6.ovpn", "proto tcp\nremote 127.0.0.1 443\n")
            from unittest.mock import patch
            import io

            with patch.object(b, "urlopen", return_value=io.BytesIO((root / "nordvpn.zip").read_bytes())):
                b.extract_archive(root, lambda message: None, "udp")
            profiles = list((root / "profiles").glob("*.ovpn"))
            self.assertEqual(len(profiles), 1)
            self.assertEqual(b.parse_profile(profiles[0])[0].protocol, "udp")

    def test_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ae72.nordvpn.com.udp_2.6.ovpn"
            path.write_text("client\nproto udp\nremote 146.70.238.179 53\n<ca>\nremote fake 22\n</ca>\n")
            result = b.parse_profile(path)
            self.assertEqual((result[0].host, result[0].port, result[0].protocol), ("146.70.238.179", 53, "udp"))

    def test_measurement(self):
        result = b.Measurement("127.0.0.1", 5, [10.0, 11.0, 50.0, 12.0])
        self.assertEqual(result.median, 11.5)
        self.assertEqual(result.jitter, 1.0)
        self.assertEqual(result.loss, 20.0)

    def test_ping_parsing(self):
        with patch.object(b.subprocess, "run") as run:
            run.return_value.stdout = "64 bytes from host: time=1.24 ms\n64 bytes from host: time=2.51 ms"
            result = b.ping("127.0.0.1", 3, 1)
            self.assertEqual(result.samples, [1.24, 2.51])
            self.assertAlmostEqual(result.loss, 100 / 3)

    def test_render(self):
        self.assertIn("┌", b.render_table(["a"], [["b"]]))
        self.assertIn("+", b.render_table(["a"], [["b"]], True))

    def test_mean_and_coloured_table(self):
        measurement = b.Measurement("127.0.0.1", 3, [10.0, 20.0, 30.0])
        self.assertEqual(measurement.mean, 20.0)
        record = b.records_for([b.Endpoint("a.ovpn", "127.0.0.1", 53, "udp", "a.ovpn")], {"127.0.0.1": measurement})[0]
        self.assertEqual(record["mean_ms"], 20.0)
        plain = b.format_results([record], 1, False)
        coloured = b.format_results([record], 1, False, colour=True)
        accessible = b.format_results([record], 1, False, colour=True, colourblind=True)
        self.assertIn("20.00 ms", plain)
        self.assertNotIn("\x1b[", plain)
        self.assertIn("\x1b[38;2;", coloured)
        self.assertNotEqual(coloured, accessible)
        self.assertEqual(b.ANSI_ESCAPE.sub("", coloured), plain)
        self.assertEqual(b.ANSI_ESCAPE.sub("", accessible), plain)
        self.assertEqual(
            [len(line) for line in plain.splitlines()],
            [len(line) for line in b.ANSI_ESCAPE.sub("", coloured).splitlines()],
        )

    def test_palette_boundaries(self):
        self.assertEqual(b.latency_rgb(0), b.latency_rgb(-5))
        self.assertEqual(b.latency_rgb(250), b.latency_rgb(999))
        self.assertNotEqual(b.latency_rgb(40), b.latency_rgb(40, True))
        self.assertEqual(b.colour_latency("—", None, enabled=True), "—")

    def test_colour_flags(self):
        with (
            patch.object(b.shutil, "which", return_value="ping"),
            patch.object(b, "execute_stage", return_value={"127.0.0.1": b.Measurement("127.0.0.1", 3, [10, 11, 12])}),
            patch.object(b, "terminal_colour_enabled", return_value=True),
            tempfile.TemporaryDirectory() as directory,
        ):
            Path(directory, "server.ovpn").write_text("proto udp\nremote 127.0.0.1 53\n")
            import io
            from contextlib import redirect_stdout

            for flag in ("--colourblind", "--colorblind"):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(b.main(["--config-dir", directory, flag, "--quiet"]), 0)
                self.assertIn("\x1b[38;2;", output.getvalue())
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(b.main(["--config-dir", directory, "--no-colour", "--quiet"]), 0)
            self.assertNotIn("\x1b[", output.getvalue())

    def test_ranking(self):
        reliable = b.Measurement("a", 3, [20, 21, 22])
        unreliable = b.Measurement("b", 3, [1])
        self.assertLess(b.rank(reliable), b.rank(unreliable))


if __name__ == "__main__":
    unittest.main()


class FilterTests(unittest.TestCase):
    def setUp(self):
        from nordvpn_filter import compile_filter, server_identity

        self.compile = compile_filter
        self.identity = server_identity
        self.uk = b.Endpoint("09150-uk2108.nordvpn.com.udp_2.6.ovpn", "89.34.98.86", 53, "udp", "uk2108.nordvpn.com")
        self.us = b.Endpoint("us17.ovpn", "1.2.3.4", 443, "tcp", "us17.nordvpn.com")
        self.nl = b.Endpoint("nl1.ovpn", "1.2.3.5", 53, "udp", "nl1.nordvpn.com")

    def test_canonical_identity_and_export(self):
        self.assertEqual(self.identity(self.uk.file), "uk2108.nordvpn.com")
        self.assertEqual(self.identity("uk715.nordvpn.com.tcp_2.6.ovpn"), "uk715.nordvpn.com")
        row = b.records_for([self.uk], {self.uk.host: b.Measurement(self.uk.host, 2, [6.1, 6.2])})[0]
        self.assertEqual(row["server"], "uk2108.nordvpn.com")
        self.assertEqual(row["config_file"], self.uk.file)
        self.assertIn("uk2108.nordvpn.com", b.format_results([row], 1, True))
        self.assertNotIn("09150-", b.format_results([row], 1, True))

    def test_boolean_precedence_and_negation(self):
        self.assertTrue(self.compile("!uk|!us")(self.uk))
        self.assertFalse(self.compile("!(uk|us)")(self.uk))
        self.assertFalse(self.compile("!(uk|us)")(self.us))
        self.assertTrue(self.compile("!(uk|us)")(self.nl))
        self.assertTrue(self.compile("(uk|nl)&protocol:udp")(self.uk))
        self.assertFalse(self.compile("(uk|nl)&protocol:udp")(self.us))
        self.assertTrue(self.compile("server:uk* & port:53")(self.uk))
        self.assertTrue(self.compile("host:*.nordvpn.com")(self.uk))

    def test_invalid_expressions(self):
        from nordvpn_filter import FilterSyntaxError

        for expression in ("", "uk|", "!(uk|us", "uk&)", "country:usa", "port:99999", "protocol:icmp", "foo", "uk us"):
            with self.subTest(expression=expression), self.assertRaises(FilterSyntaxError):
                self.compile(expression)

    def test_filter_applies_before_probes(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(b.shutil, "which", return_value="ping"),
            patch.object(b, "execute_stage") as stage,
        ):
            path = Path(directory) / "09150-uk2108.nordvpn.com.udp_2.6.ovpn"
            path.write_text("proto udp\nremote 89.34.98.86 53\n")
            import contextlib
            import io

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                b.main(["--config-dir", directory, "--filter=!(uk|us)"])
            self.assertEqual(error.exception.code, 2)
            stage.assert_not_called()
