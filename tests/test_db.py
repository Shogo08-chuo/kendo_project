import os
import tempfile
import unittest

from kendo_analyzer.db import DetectionRepository
from kendo_analyzer.models import Detection


class DetectionRepositoryTest(unittest.TestCase):
    def test_saves_and_reads_recent_detections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "kendo.db")
            repository = DetectionRepository(db_path)

            repository.save(Detection("men", 90.5, timestamp_sec=12.0))
            repository.save(Detection("do", 84.0, timestamp_sec=20.0))

            recent = repository.recent(limit=2)

            self.assertEqual([item.name for item in recent], ["do", "men"])
            self.assertEqual(recent[0].timestamp_sec, 20.0)


if __name__ == "__main__":
    unittest.main()
