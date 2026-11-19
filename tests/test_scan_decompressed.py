import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "scan_decompressed.py"
spec = importlib.util.spec_from_file_location("scan_decompressed", MODULE)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)

class SignatureScanTests(unittest.TestCase):
    def test_finds_multiple_signatures_in_offset_order(self):
        data = b"xxJBOYyyDDS zSHDC"
        self.assertEqual(scanner.scan(data), [
            (2, "JBOY model"),
            (8, "DDS texture"),
            (14, "SHDC container"),
        ])

    def test_no_hits(self):
        self.assertEqual(scanner.scan(b"unknown bytes"), [])

    def test_repeated_signature(self):
        self.assertEqual(scanner.scan(b"BPE BPE "), [
            (0, "BPE compressed resource"),
            (4, "BPE compressed resource"),
        ])

if __name__ == "__main__":
    unittest.main()
