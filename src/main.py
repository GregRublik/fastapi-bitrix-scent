from fastapi import FastAPI
from a2wsgi import ASGIMiddleware
from loguru import logger
from fastapi.staticfiles import StaticFiles


from src.logger import setup_logger

setup_logger()
logger.info("Application starting...")

from src.api.v1.routing import auth, concord, forms, universal, user, contacts
from src.exception_handlers import exception_handlers
from src.middleware.logging_middleware import setup_logging_middleware


app = FastAPI(exception_handlers=exception_handlers)
setup_logging_middleware(app)
app.include_router(universal.router)
app.include_router(auth.router)
app.include_router(concord.router)
app.include_router(forms.router)
app.include_router(user.router)
app.include_router(contacts.contacts)


app.mount("/static", StaticFiles(directory="src/static"), name="static")

application = ASGIMiddleware(app)
