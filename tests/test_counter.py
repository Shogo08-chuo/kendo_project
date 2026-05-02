import unittest

from kendo_analyzer.counter import StrikeCounter
from kendo_analyzer.models import Detection


class StrikeCounterTest(unittest.TestCase):
    def test_counts_target_waza_with_time_deduplication(self):
        counter = StrikeCounter(dedupe_seconds=5)

        self.assertTrue(counter.register(Detection("men", 91.0, timestamp_sec=0)))
        self.assertFalse(counter.register(Detection("men", 88.0, timestamp_sec=4)))
        self.assertTrue(counter.register(Detection("men", 95.0, timestamp_sec=6)))

        self.assertEqual(counter.counts["men"], 2)
        self.assertEqual(len(counter.accepted_detections), 2)

    def test_ignores_non_target_labels(self):
        counter = StrikeCounter()

        accepted = counter.register(Detection("person", 99.0, timestamp_sec=1))

        self.assertFalse(accepted)
        self.assertEqual(counter.counts, {"men": 0, "kote": 0, "do": 0})

    def test_accepts_case_insensitive_waza_names(self):
        counter = StrikeCounter()

        self.assertTrue(counter.register(Detection("Kote", 82.0, timestamp_sec=10)))

        self.assertEqual(counter.counts["kote"], 1)


if __name__ == "__main__":
    unittest.main()
