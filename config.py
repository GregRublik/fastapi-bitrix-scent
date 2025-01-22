from os import getenv
from dotenv import load_dotenv


load_dotenv()

portal_url = getenv('PORTAL_URL')
hosting_url = getenv('HOSTING_URL')
secret = getenv('CLIENT_SECRET')
client_id = getenv('CLIENT_ID')
key_405 = getenv('API_KEY_405')
