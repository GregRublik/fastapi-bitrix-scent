from os import getenv
from dotenv import load_dotenv
from loguru import logger
from fastapi.templating import Jinja2Templates
from session_manager import SessionManager


logger.add(
    "logs/debug.log",
    format="{time} - {level} - {message}",
    level="INFO",
    rotation="5 MB",
    compression="zip"
)

templates = Jinja2Templates(directory="templates")

session_manager = SessionManager.get_instance()

load_dotenv()

portal_url = getenv('PORTAL_URL')
hosting_url = getenv('HOSTING_URL')
secret = getenv('CLIENT_SECRET')
client_id = getenv('CLIENT_ID')
key_405 = getenv('API_KEY_405')
