from os import getenv
from models import InvalidToken


def check_token(client_secret):
    assert client_secret == getenv("CLIENT_SECRET"), "Invalid Token"


# def check_token(client_secret):
#     if client_secret != getenv("CLIENT_SECRET"):
#         raise InvalidToken
