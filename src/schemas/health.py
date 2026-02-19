from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    database: str  # "connected" | "disconnected"
    version: str
    built_by: str
