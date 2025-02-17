from core.config import settings


def check_token(client_secret):
    assert client_secret == settings.client_secret, "Invalid Token"
