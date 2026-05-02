import os
from dataclasses import dataclass
from typing import Mapping, Optional


AWS_REGION_DEFAULT = "ap-northeast-1"
DB_PATH_DEFAULT = "kendo_app.db"


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class AppConfig:
    model_arn: str
    region: str = AWS_REGION_DEFAULT
    db_path: str = DB_PATH_DEFAULT
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    image_min_confidence: float = 1.0
    video_min_confidence: float = 50.0
    frame_interval_seconds: float = 2.0
    dedupe_seconds: float = 5.0


def _get_value(name: str, secrets=None, env: Mapping[str, str] = os.environ, default=None):
    if secrets is not None:
        try:
            value = secrets.get(name)
            if value not in (None, ""):
                return value
        except Exception:
            pass
    return env.get(name, default)


def _get_float(name: str, secrets=None, env: Mapping[str, str] = os.environ, default=0.0) -> float:
    value = _get_value(name, secrets=secrets, env=env, default=default)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name}には数値を設定してください。") from exc


def load_config(secrets=None, env: Mapping[str, str] = os.environ) -> AppConfig:
    model_arn = _get_value("AWS_MODEL_ARN", secrets=secrets, env=env)
    if not model_arn:
        raise ConfigError("AWS_MODEL_ARNが未設定です。Secretsまたは環境変数に設定してください。")

    return AppConfig(
        model_arn=model_arn,
        region=_get_value("AWS_REGION", secrets=secrets, env=env, default=AWS_REGION_DEFAULT),
        db_path=_get_value("DB_PATH", secrets=secrets, env=env, default=DB_PATH_DEFAULT),
        aws_access_key_id=_get_value("AWS_ACCESS_KEY_ID", secrets=secrets, env=env),
        aws_secret_access_key=_get_value("AWS_SECRET_ACCESS_KEY", secrets=secrets, env=env),
        image_min_confidence=_get_float(
            "IMAGE_MIN_CONFIDENCE", secrets=secrets, env=env, default=1.0
        ),
        video_min_confidence=_get_float(
            "VIDEO_MIN_CONFIDENCE", secrets=secrets, env=env, default=50.0
        ),
        frame_interval_seconds=_get_float(
            "FRAME_INTERVAL_SECONDS", secrets=secrets, env=env, default=2.0
        ),
        dedupe_seconds=_get_float("DEDUPE_SECONDS", secrets=secrets, env=env, default=5.0),
    )
