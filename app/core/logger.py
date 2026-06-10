import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings

settings.log_path.parent.mkdir(parents=True, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")

_file_handler = RotatingFileHandler(
    settings.log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _console_handler])


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
