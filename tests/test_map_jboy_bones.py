import unittest
from tools.map_jboy_bones import inspect, classify

class BoneMapTests(unittest.TestCase):
    def test_name_labels_are_heuristic(self):
        self.assertIn("pelvis", classify("Pelvis"))
        self.assertIn("head", classify("Head_Bone"))
        self.assertIn("left_arm", classify("LeftArm"))
        self.assertIn("right_leg", classify("RightLeg"))

    def test_report_preserves_candidate_parent_and_warns(self):
        report = inspect({"bones":[
            {"index":0,"name":"Root","parent_index_candidate":None},
            {"index":1,"name":"Pelvis","parent_index_candidate":0}]})
        self.assertEqual(report["bones"][1]["parent_index_candidate"],0)
        self.assertIn("not an FBX",report["interpretation_warning"])

    def test_self_parent_invalid(self):
        report = inspect({"bones":[{"index":0,"name":"root","parent_index_candidate":0}]})
        self.assertEqual(len(report["invalid_parent_candidates"]),1)

if __name__ == "__main__":
    unittest.main()
