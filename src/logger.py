from loguru import logger
import os
import sys


def setup_logger():
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, "app.log")

    # Убираем дефолтный логгер
    logger.remove()

    # Консоль (для локальной разработки)
    logger.add(
        sys.stdout,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        colorize=True,
    )

    # Файл (для сервера)
    logger.add(
        log_file,
        level="INFO",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
    )

    logger.info("Logger initialized")
