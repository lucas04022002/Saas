from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool = True
    message: str
    data: Any | None = None


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
