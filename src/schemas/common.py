from pydantic import BaseModel, ConfigDict


class Pagination(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "per_page": 20,
                "total": 42,
                "total_pages": 3,
            }
        }
    )

    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse[T](BaseModel):
    data: list[T]
    pagination: Pagination


class ErrorDetail(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "email",
                "message": "value is not a valid email address",
            }
        }
    )

    field: str
    message: str


class ErrorCode(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "UNAUTHORIZED",
                "message": "Could not validate credentials",
                "details": None,
            }
        }
    )

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Could not validate credentials",
                    "details": None,
                }
            }
        }
    )

    error: ErrorCode
