import unittest

from kendo_analyzer.config import ConfigError, load_config


class LoadConfigTest(unittest.TestCase):
    def test_loads_required_and_optional_values_from_env_mapping(self):
        config = load_config(
            env={
                "AWS_MODEL_ARN": "arn:example",
                "AWS_REGION": "ap-northeast-1",
                "DB_PATH": "tmp/test.db",
                "VIDEO_MIN_CONFIDENCE": "55",
                "FRAME_INTERVAL_SECONDS": "1.5",
                "DEDUPE_SECONDS": "4",
            }
        )

        self.assertEqual(config.model_arn, "arn:example")
        self.assertEqual(config.db_path, "tmp/test.db")
        self.assertEqual(config.video_min_confidence, 55.0)
        self.assertEqual(config.frame_interval_seconds, 1.5)
        self.assertEqual(config.dedupe_seconds, 4.0)

    def test_requires_model_arn(self):
        with self.assertRaises(ConfigError):
            load_config(env={})

    def test_rejects_invalid_numeric_values(self):
        with self.assertRaises(ConfigError):
            load_config(env={"AWS_MODEL_ARN": "arn:example", "DEDUPE_SECONDS": "fast"})


if __name__ == "__main__":
    unittest.main()
