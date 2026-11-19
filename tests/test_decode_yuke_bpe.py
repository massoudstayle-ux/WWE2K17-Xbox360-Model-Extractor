import importlib.util
import struct
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "decode_yuke_bpe.py"
spec = importlib.util.spec_from_file_location("decode_yuke_bpe", MODULE)
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)

def identity_bpe(data: bytes) -> bytes:
    # Code table: identity mappings for 0..127 via the run marker, then 128..255.
    payload = bytearray([255, 128, 126])
    payload.extend(range(129, 256))
    payload.extend(struct.pack("<H", len(data)))
    payload.extend(data)
    header = b"BPE " + struct.pack("<III", 0x100, len(payload), len(data))
    return header + payload

class YukesBPETests(unittest.TestCase):
    def test_identity_code_table_round_trip(self):
        expected = bytes([0, 1, 2, 127, 128, 200, 255])
        self.assertEqual(decoder.decode_yuke_bpe(identity_bpe(expected)), expected)

    def test_rejects_wrong_header(self):
        with self.assertRaises(decoder.BPEError):
            decoder.decode_yuke_bpe(b"NOPE" + bytes(30))

    def test_rejects_declared_length_mismatch(self):
        blob = bytearray(identity_bpe(b"abc"))
        struct.pack_into("<I", blob, 12, 4)
        with self.assertRaises(decoder.BPEError):
            decoder.decode_yuke_bpe(bytes(blob))

if __name__ == "__main__":
    unittest.main()
