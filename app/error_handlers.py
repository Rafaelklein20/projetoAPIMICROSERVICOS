from fastapi import Request
from fastapi.responses import JSONResponse
from app.errors import ApiError

async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )