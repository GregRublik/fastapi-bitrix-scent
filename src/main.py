from a2wsgi import ASGIMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.v1.routing import auth, concord, forms, universal, user, contacts
from src.exception_handlers import exception_handlers
from src.logging_config import setup_logging

setup_logging()

app = FastAPI(exception_handlers=exception_handlers)
app.include_router(universal.router)
app.include_router(auth.router)
app.include_router(concord.router)
app.include_router(forms.router)
app.include_router(user.router)
app.include_router(contacts.contacts)


app.mount("/static", StaticFiles(directory="src/static"), name="static")

application = ASGIMiddleware(app)
