from loguru import logger
from time import time
from fastapi import Request

def setup_logging_middleware(app):
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time()
        try:
            response = await call_next(request)
        except Exception as e:
            duration = time() - start_time
            # Логируем исключение
            logger.exception(
                f"Exception on request {request.method} {request.url.path} "
                f"Duration: {duration:.4f}s"
            )
            raise  # обязательно пробрасываем дальше, чтобы FastAPI вернул 500
        else:
            duration = time() - start_time
            # Логируем обычный запрос
            logger.info(
                f"{request.method} {request.url.path} "
                f"Status: {response.status_code} "
                f"Duration: {duration:.4f}s"
            )
            return response