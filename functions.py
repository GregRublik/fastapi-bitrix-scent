from os import getenv
from models.models import InvalidToken


def check_token(client_secret):
    assert client_secret == getenv("CLIENT_SECRET"), "Invalid Token"
