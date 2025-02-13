from pydantic import BaseModel
from typing import Dict


class InvalidToken(Exception):
    pass


class MainHandler(BaseModel):
    client_secret: str
    method: str
    params: Dict[str, Dict[str, Dict[str, str | Dict] | str | int] | int | str]


class Params(BaseModel):
    form_id: str
    user_id: str
    points: str
    max_points: str
    form_name: str
    answer_id: str


class FormRequest(BaseModel):
    jsonrpc: str
    method: str
    params: Params
    id: int
