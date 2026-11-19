import struct
import unittest
from tools.analyze_jboy_skinning import FormatError, inspect

def make_jboy(vertex_count=2, weight_blocks=2, span_bytes=None):
    data=bytearray(0x400)
    data[:4]=b"JBOY"
    struct.pack_into(">I",data,0x18,1)
    struct.pack_into(">I",data,0x1C,0x20)
    desc=0x28
    struct.pack_into(">I",data,desc,vertex_count)
    struct.pack_into(">I",data,desc+0x5C,weight_blocks)
    weight_ptr=0x200
    expected=vertex_count*weight_blocks*8
    uv_ptr=weight_ptr+(expected if span_bytes is None else span_bytes)
    struct.pack_into(">I",data,desc+0x6C,weight_ptr-8)
    struct.pack_into(">I",data,desc+0x70,uv_ptr-8)
    # Two bones; one active influence plus sentinel per vertex.
    for v in range(vertex_count):
        off=weight_ptr+v*weight_blocks*8
        struct.pack_into("<I",data,off, v%2)
        struct.pack_into(">f",data,off+4,1.0)
        if weight_blocks>1:
            struct.pack_into("<I",data,off+8,255)
            struct.pack_into(">f",data,off+12,0.0)
    struct.pack_into(">I",data,0x20,2)
    return bytes(data)

class SkinningBufferTests(unittest.TestCase):
    def test_exact_span_and_decoding(self):
        report=inspect(make_jboy(),samples=1)
        self.assertTrue(report["all_weight_spans_match"])
        self.assertEqual(report["meshes"][0]["valid_influence_slots"],2)
        self.assertEqual(report["meshes"][0]["sentinel_slots"],2)
        self.assertEqual(report["vertices_with_weight_sum_outside_tolerance"],0)
        self.assertEqual(report["meshes"][0]["sample_vertices"][0]["slots"][0]["bone_index_candidate"],0)

    def test_mismatched_span_is_not_accepted(self):
        report=inspect(make_jboy(span_bytes=8),samples=0)
        self.assertFalse(report["all_weight_spans_match"])

    def test_bad_magic_is_rejected(self):
        with self.assertRaises(FormatError): inspect(b"NOPE"+bytes(256))

    def test_out_of_bounds_buffer_is_rejected(self):
        data=bytearray(make_jboy())
        struct.pack_into(">I",data,0x28+0x70,0x7FFFFFF0)
        with self.assertRaises(FormatError): inspect(bytes(data))

    def test_invalid_bone_index_is_reported(self):
        data=bytearray(make_jboy())
        struct.pack_into("<I",data,0x200,7)
        report=inspect(bytes(data),samples=1)
        self.assertEqual(report["invalid_bone_index_slots"],1)

if __name__=="__main__": unittest.main()
