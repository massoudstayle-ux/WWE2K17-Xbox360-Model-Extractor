import unittest
from tools.bone_transform_diagnostics import inspect

class DiagnosticsTests(unittest.TestCase):
    def test_stats_and_parent_cycle(self):
        report = inspect({"bones":[
            {"index":0,"name":"root","parent_index_candidate":1,"local_position_candidate":[0,0,0,1]},
            {"index":1,"name":"child","parent_index_candidate":0,"local_position_candidate":[3,4,0,1]},
        ]})
        self.assertEqual(report["candidate_parent_cycle_count"],1)
        self.assertEqual(report["vector_field_statistics"]["local_position_candidate"]["magnitude_max"],5.0)

    def test_invalid_parent_and_bad_vector(self):
        report = inspect({"bones":[{"index":0,"parent_index_candidate":9,"local_position_candidate":[float("nan"),0,0]}]})
        self.assertEqual(report["candidate_parent_invalid_count"],1)
        self.assertFalse(report["bones"][0]["fields"]["local_position_candidate"]["valid_numeric_vector"])

    def test_empty(self):
        report = inspect({"bones":[]})
        self.assertEqual(report["bone_count"],0)
        self.assertEqual(report["candidate_parent_cycle_count"],0)

if __name__ == "__main__":
    unittest.main()
