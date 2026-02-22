from loguru import logger
from time import time
from fastapi import Request

def setup_logging_middleware(app):
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time()

        response = await call_next(request)

        duration = time() - start_time
        logger.info(
            f"{request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {duration:.4f}s"
        )

        return response