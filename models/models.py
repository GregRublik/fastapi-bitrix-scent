from pydantic import BaseModel
from typing import Dict, Any, List


class InvalidToken(Exception):
    pass


class MainHandler(BaseModel):
    client_secret: str
    method: str
    params: Dict[str, Dict[str, Dict[str, str | Dict] | str | int] | int | str]
