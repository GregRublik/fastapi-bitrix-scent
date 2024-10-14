from os import getenv
from dotenv import load_dotenv


load_dotenv()

portal_url = getenv('PORTAL_URL')
hosting_url = getenv('HOSTING_URL')
secret = getenv('CLIENT_SECRET')
client_id = getenv('CLIENT_ID')
reg_ru_hosting_name = getenv('REG_RU')
