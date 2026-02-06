import platform
import uvicorn
from a2wsgi import ASGIMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import logger, settings
from api.v1.routing import auth, concord, forms, universal, user, contacts
import sentry_sdk


sentry_sdk.init(
    dsn=settings.sentry_url,
    send_default_pii=True,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = FastAPI()
app.include_router(universal.app_univers)
app.include_router(auth.app_auth)
app.include_router(concord.app_concord)
app.include_router(forms.app_forms)
app.include_router(user.app_user)
app.include_router(contacts.contacts)
app.mount("src/static", StaticFiles(directory="src/static"), name="static")

application = ASGIMiddleware(app)

scheduler = AsyncIOScheduler()


if __name__ == "__main__":
    try:
        if platform.system() == "Windows":
            uvicorn.run(
                app,
                host="127.0.0.1",
                log_config="logs/log_config.json",
                use_colors=True,
                log_level="info",
                loop="asyncio"
            )
        else:
            uvicorn.run(
                application,
                host="0.0.0.0",
                log_config="logs/log_config.json",
                use_colors=True,
                log_level="info",
                loop="asyncio"
            )
    except Exception as e:
        logger.error(f"Error launch app: {e}")
