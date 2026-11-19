import importlib.util
import struct
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "parse_hspc.py"
spec = importlib.util.spec_from_file_location("parse_hspc", MODULE)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

def make_fixture():
    data = bytearray(0x2800)
    data[0:4] = b"HSPC"
    struct.pack_into("<I", data, 0x18, 0x28)
    struct.pack_into("<I", data, 0x38, 1)
    data[0x800:0x808] = bytes.fromhex("0102030405060708")
    struct.pack_into("<II", data, 0x1000, 3, 0x10)
    data[0x1800:0x1804] = b"SHDC"
    struct.pack_into("<I", data, 0x1800 + 0x0C, 1)
    struct.pack_into("<I", data, 0x1800 + 0x1C, 0x60)
    struct.pack_into("<I", data, 0x1800 + 0x20, 0x10)
    struct.pack_into("<IIQ", data, 0x1800 + 0x60, 0xA, 0x80, 0x20)
    data[0x1880:0x1884] = b"BPE "
    return bytes(data)

class HSPCParserTests(unittest.TestCase):
    def test_parses_hspc_and_shdc_tables(self):
        result = parser.analyze(make_fixture())
        self.assertEqual(len(result["hspc_entries"]), 1)
        self.assertEqual(result["hspc_entries"][0]["offset"], 0x1800)
        self.assertEqual(result["hspc_entries"][0]["magic"], "SHDC")
        self.assertEqual(len(result["shdc_entries"]), 1)
        self.assertEqual(result["shdc_entries"][0]["offset"], 0x1880)
        self.assertEqual(result["shdc_entries"][0]["magic"], "BPE ")

    def test_rejects_non_hspc(self):
        with self.assertRaises(parser.FormatError):
            parser.analyze(b"NOPE" + bytes(100))

    def test_rejects_out_of_bounds_hspc_entry(self):
        data = bytearray(make_fixture())
        struct.pack_into("<II", data, 0x1000, 0xFFFF, 0x100)
        with self.assertRaises(parser.FormatError):
            parser.analyze(bytes(data))

if __name__ == "__main__":
    unittest.main()
