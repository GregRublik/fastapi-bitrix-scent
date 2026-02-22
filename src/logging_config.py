import logging.config
import json
import os


def setup_logging():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(BASE_DIR, "logs", "log_config.json")

    with open(config_path, "r") as f:
        config = json.load(f)

    logging.config.dictConfig(config)
