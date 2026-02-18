import platform
import uvicorn
from a2wsgi import ASGIMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import logger, settings
from api.v1.routing import auth, concord, forms, universal, user, contacts
from exception_handlers import exception_handlers

app = FastAPI(exception_handlers=exception_handlers)
app.include_router(universal.router)
app.include_router(auth.router)
app.include_router(concord.router)
app.include_router(forms.router)
app.include_router(user.router)
app.include_router(contacts.contacts)


app.mount("/static", StaticFiles(directory="src/static"), name="static")

if platform.system() == "Windows":
    application = ASGIMiddleware(app)
else:
    application = app



if __name__ == "__main__":
    try:
        uvicorn.run(
            application,
            host=settings.host,
            log_config="logs/log_config.json",
            use_colors=True,
            log_level="info",
            loop="asyncio"
        )
    except Exception as e:
        logger.error(f"Error launch app: {e}")
