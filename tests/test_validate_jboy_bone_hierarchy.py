import unittest
from tools.validate_jboy_bone_hierarchy import inspect

class BoneHierarchyTests(unittest.TestCase):
    def test_two_roots_valid_tree(self):
        report=inspect({"bones":[
            {"index":0,"name":"root","parent_index_candidate":None},
            {"index":1,"name":"pelvis","parent_index_candidate":0},
            {"index":2,"name":"leg","parent_index_candidate":1}]})
        self.assertTrue(report["hierarchy_structurally_valid"])
        self.assertEqual([x["index"] for x in report["root_bones"]],[0])

    def test_out_of_range_parent(self):
        report=inspect({"bones":[{"index":0,"name":"root","parent_index_candidate":8}]})
        self.assertFalse(report["hierarchy_structurally_valid"])
        self.assertEqual(len(report["invalid_parent_records"]),1)

    def test_cycle_detected(self):
        report=inspect({"bones":[
            {"index":0,"name":"a","parent_index_candidate":1},
            {"index":1,"name":"b","parent_index_candidate":0}]})
        self.assertFalse(report["hierarchy_structurally_valid"])
        self.assertTrue(report["cycle_start_bones"])

if __name__=="__main__": unittest.main()
