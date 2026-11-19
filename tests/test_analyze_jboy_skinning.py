import struct
import unittest

from tools.analyze_jboy_skinning import FormatError, inspect


def make_jboy(vertex_count=2, weight_blocks=1, span_bytes=None):
    data = bytearray(0x400)
    data[:4] = b"JBOY"
    struct.pack_into(">I", data, 0x18, 1)       # one mesh
    struct.pack_into(">I", data, 0x1C, 0x20)   # descriptor table at 0x28
    desc = 0x28
    struct.pack_into(">I", data, desc, vertex_count)
    struct.pack_into(">I", data, desc + 0x5C, weight_blocks)
    weight_ptr = 0x200
    expected = vertex_count * weight_blocks * 8
    uv_ptr = weight_ptr + (expected if span_bytes is None else span_bytes)
    struct.pack_into(">I", data, desc + 0x6C, weight_ptr - 8)
    struct.pack_into(">I", data, desc + 0x70, uv_ptr - 8)
    return bytes(data)


class SkinningBufferTests(unittest.TestCase):
    def test_exact_span_is_reported(self):
        report = inspect(make_jboy(), samples=1)
        self.assertTrue(report["all_weight_spans_match"])
        self.assertEqual(report["meshes"][0]["expected_vertex_times_blocks_times_8"], 16)

    def test_mismatched_span_is_not_accepted(self):
        report = inspect(make_jboy(span_bytes=8), samples=0)
        self.assertFalse(report["all_weight_spans_match"])
        self.assertFalse(report["meshes"][0]["span_matches_expected"])

    def test_bad_magic_is_rejected(self):
        with self.assertRaises(FormatError):
            inspect(b"NOPE" + bytes(256))

    def test_out_of_bounds_buffer_is_rejected(self):
        data = bytearray(make_jboy())
        struct.pack_into(">I", data, 0x28 + 0x70, 0x7FFFFFF0)
        with self.assertRaises(FormatError):
            inspect(bytes(data))


if __name__ == "__main__":
    unittest.main()
