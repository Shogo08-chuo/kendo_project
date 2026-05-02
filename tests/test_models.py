import unittest

from kendo_analyzer.models import best_detection, detection_from_label, is_target_waza


class DetectionModelTest(unittest.TestCase):
    def test_detection_from_rekognition_label(self):
        detection = detection_from_label({"Name": "men", "Confidence": 93.2}, timestamp_sec=3)

        self.assertEqual(detection.name, "men")
        self.assertEqual(detection.confidence, 93.2)
        self.assertEqual(detection.timestamp_sec, 3)

    def test_best_detection_uses_highest_confidence(self):
        detection = best_detection(
            [
                {"Name": "men", "Confidence": 60.0},
                {"Name": "kote", "Confidence": 91.5},
            ]
        )

        self.assertEqual(detection.name, "kote")

    def test_target_waza_check_is_case_insensitive(self):
        self.assertTrue(is_target_waza("Do"))
        self.assertFalse(is_target_waza("person"))


if __name__ == "__main__":
    unittest.main()
