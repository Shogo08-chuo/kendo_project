import os

from kendo_analyzer.config import DB_PATH_DEFAULT
from kendo_analyzer.db import DetectionRepository


def init_db():
    db_path = os.getenv("DB_PATH", DB_PATH_DEFAULT)
    repository = DetectionRepository(db_path)
    repository.init_db()
    print(f"データベース({db_path})を初期化しました。")


if __name__ == "__main__":
    init_db()
