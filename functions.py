from os import getenv


def check_token(client_secret):
    assert client_secret == getenv("CLIENT_SECRET"), "Invalid Token"
