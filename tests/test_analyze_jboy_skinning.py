import struct
import unittest

from tools.analyze_jboy_skinning import FormatError, inspect


def make_jboy(local_indices=(0, 1), weights=(0.75, 0.25), palette=(3, 1)):
    data = bytearray(0x400)
    data[:4] = b"JBOY"
    struct.pack_into(">I", data, 0x18, 1)       # one mesh
    struct.pack_into(">I", data, 0x1C, 0x20)    # mesh table at 0x28
    struct.pack_into(">I", data, 0x20, 3)       # three bones
    desc = 0x28
    struct.pack_into(">I", data, desc, 1)       # one vertex
    struct.pack_into(">I", data, desc + 0x08, len(palette))
    for i, bone in enumerate(palette):
        struct.pack_into(">I", data, desc + 0x0C + i * 4, bone)
    struct.pack_into(">I", data, desc + 0x5C, len(local_indices))
    weight_offset = 0x200
    uv_offset = weight_offset + len(local_indices) * 8
    struct.pack_into(">I", data, desc + 0x6C, weight_offset - 8)
    struct.pack_into(">I", data, desc + 0x70, uv_offset - 8)
    for i, (local, weight) in enumerate(zip(local_indices, weights)):
        data[weight_offset + i * 8] = local
        data[weight_offset + i * 8 + 1:weight_offset + i * 8 + 4] = bytes(3)
        struct.pack_into(">f", data, weight_offset + i * 8 + 4, weight)
    return bytes(data)


class SkinningPaletteTests(unittest.TestCase):
    def test_local_indices_resolve_to_global_bones(self):
        report = inspect(make_jboy())
        self.assertTrue(report["all_checks_passed"])
        self.assertEqual(report["global_bone_indices_used"], [0, 2])
        slots = report["meshes"][0]["sample_vertices"][0]["slots"]
        self.assertEqual([s["global_bone_index"] for s in slots], [2, 0])

    def test_rejects_local_index_outside_mesh_palette(self):
        report = inspect(make_jboy(local_indices=(0, 2), weights=(0.5, 0.5)))
        self.assertFalse(report["all_checks_passed"])
        self.assertEqual(report["invalid_palette_local_indices"], 1)

    def test_rejects_weight_sum_that_is_not_one(self):
        report = inspect(make_jboy(weights=(0.6, 0.2)))
        self.assertFalse(report["all_checks_passed"])
        self.assertEqual(report["vertices_with_weight_sum_outside_tolerance"], 1)

    def test_rejects_palette_bone_outside_model(self):
        with self.assertRaises(FormatError):
            inspect(make_jboy(palette=(4, 1)))

    def test_rejects_nonzero_influence_padding(self):
        data = bytearray(make_jboy())
        data[0x201] = 1
        report = inspect(bytes(data))
        self.assertFalse(report["all_checks_passed"])
        self.assertGreater(report["invalid_weight_slots"], 0)


if __name__ == "__main__":
    unittest.main()
