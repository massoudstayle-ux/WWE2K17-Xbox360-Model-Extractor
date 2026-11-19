import struct
import unittest
from tools.inspect_jboy_bone_fields import inspect, FormatError

class BoneFieldInspectionTests(unittest.TestCase):
    def sample(self):
        data=bytearray(0x100+0x50)
        data[:4]=b"JBOY"
        struct.pack_into(">I",data,0x20,1)
        struct.pack_into(">I",data,0x28,0xF8) # +8 => 0x100
        data[0x100:0x110]=b"root\\0"+b"\\0"*11
        struct.pack_into(">I",data,0x130,0xFFFFFFFF)
        for off, vals in ((0x10,(1,2,3,4)),(0x20,(5,6,7,8)),(0x30,(9,10,11,12)),(0x40,(13,14,15,16))):
            struct.pack_into(">4f",data,0x100+off,*vals)
        return bytes(data)
    def test_raw_candidate_offsets_preserved(self):
        result=inspect(self.sample())
        self.assertEqual(result["bone_count"],1)
        b=result["bones"][0]
        self.assertEqual(b["candidate_fields"]["offset_0x10"]["float32_be_candidates"],[1,2,3,4])
        self.assertEqual(b["candidate_fields"]["offset_0x30"]["float32_be_candidates"],[9,10,11,12])
        self.assertEqual(b["parent_u32_at_0x30"],0xFFFFFFFF)
        self.assertIn("semantics",result["warning"])
    def test_invalid_magic(self):
        with self.assertRaises(FormatError): inspect(b"BAD!")
