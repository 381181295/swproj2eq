import tempfile
import unittest
from pathlib import Path

from swproj2eq.core.parser import parse_swproj


class ParserTests(unittest.TestCase):
    def test_invalid_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.swproj"
            p.write_bytes(b"not-a-real-swproj")
            with self.assertRaises(ValueError):
                parse_swproj(str(p))


if __name__ == "__main__":
    unittest.main()
