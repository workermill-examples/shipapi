from pydantic import BaseModel


class Pagination(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse[T](BaseModel):
    data: list[T]
    pagination: Pagination


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorCode(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorCode
