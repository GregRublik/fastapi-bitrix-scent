from fastapi import Request
from fastapi.responses import JSONResponse
from exceptions import ErrorRequestBitrix
from typing import Dict, Any

# Определяем обработчики как обычные функции
async def error_request_bitrix_handler(request: Request, exc: ErrorRequestBitrix) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error": "Bitrix request failed"}
    )

async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error": "Validation error"}
    )

# Создаем словарь для удобного импорта
exception_handlers: Dict[Any, Any] = {
    ErrorRequestBitrix: error_request_bitrix_handler,
    # добавьте другие обработчики здесь
}
