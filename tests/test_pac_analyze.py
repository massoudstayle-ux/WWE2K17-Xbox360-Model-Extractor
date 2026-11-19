import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "pac_analyze.py"
spec = importlib.util.spec_from_file_location("pac_analyze", MODULE)
pac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pac)

class PacAnalyzeTests(unittest.TestCase):
    def test_entropy_empty_and_uniform(self):
        self.assertEqual(pac.entropy(b""), 0.0)
        self.assertEqual(pac.entropy(b"AAAA"), 0.0)

    def test_printable_strings_offsets(self):
        self.assertEqual(pac.printable_strings(b"\x00HELLO\x00WORLD!", 5),
                         [(1, "HELLO"), (7, "WORLD!")])

    def test_signature_detection(self):
        self.assertEqual(pac.signature_hits(b"xxDDS yy"), [(2, "DDS texture")])

    def test_aligned_values_bounds(self):
        data = (128).to_bytes(4, "little") + (9999).to_bytes(4, "little")
        self.assertEqual(pac.aligned_values(data, "little", 200), [(0, 128)])

if __name__ == "__main__":
    unittest.main()
