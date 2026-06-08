from bson.errors import InvalidId
from fastapi import Request
from fastapi.responses import JSONResponse


async def invalid_object_id_handler(_request: Request, _exc: InvalidId) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})
