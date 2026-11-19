import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "export_jboy_obj.py"
spec = importlib.util.spec_from_file_location("export_jboy_obj", MODULE)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

class JBOYExportTests(unittest.TestCase):
    def test_rejects_unknown_model_magic(self):
        with self.assertRaises(exporter.JBOYError):
            exporter.parse_model(b"NOPE" + bytes(256))

    def test_triangle_strip_handles_degenerate_restart(self):
        # Construct the face block expected at faces_offset + 8.
        import struct
        data = bytearray(64)
        struct.pack_into(">I", data, 12, 6)
        for i, value in enumerate([0, 1, 2, 2, 3, 3]):
            struct.pack_into(">H", data, 20 + i*2, value)
        faces, count = exporter.parse_triangle_strips(bytes(data), 0)
        self.assertEqual(count, 6)
        self.assertEqual(faces, [(1, 3, 2)])

if __name__ == "__main__":
    unittest.main()
