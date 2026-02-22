import logging
import logging.config
import json
import os


def setup_logging():
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # noqa
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT) # noqa

    logs_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    config_path = os.path.join(logs_dir, "log_config.json")

    with open(config_path) as f:
        config = json.load(f)

    config["handlers"]["file"]["filename"] = os.path.join(logs_dir, "app.log")

    # 🔥 ВАЖНО
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.config.dictConfig(config)

    print("LOGGING INITIALIZED")