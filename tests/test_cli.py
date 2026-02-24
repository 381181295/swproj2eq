import unittest

from swproj2eq.cli import normalize_legacy_args


class CliTests(unittest.TestCase):
    def test_legacy_export_args_are_normalized(self):
        argv = ["/tmp/a.swproj", "--outdir", "/tmp/out"]
        normalized = normalize_legacy_args(argv)
        self.assertEqual(normalized[:3], ["export", "--profile", "/tmp/a.swproj"])

    def test_subcommand_args_unchanged(self):
        argv = ["status", "--json"]
        self.assertEqual(normalize_legacy_args(argv), argv)


if __name__ == "__main__":
    unittest.main()
