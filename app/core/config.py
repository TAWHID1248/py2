from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "BM2Ultra"
    app_version: str = "1.0.0"

    db_path: Path = BASE_DIR / "data" / "EmailTrackDB.db"
    log_path: Path = BASE_DIR / "logs" / "bm2ultra.log"
    attachments_dir: Path = BASE_DIR / "data" / "attachments"
    templates_dir: Path = BASE_DIR / "data" / "templates"

    tracking_host: str = "127.0.0.1"
    tracking_port: int = 8765

    send_thread_count: int = 4
    default_throttle_delay: float = 1.0  # seconds between sends

    model_config = {"env_prefix": "BM2_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
