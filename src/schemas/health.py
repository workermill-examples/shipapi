from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "database": "connected",
                "version": "1.0.0",
                "built_by": "ShipAPI",
            }
        }
    )

    status: str  # "ok" | "degraded"
    database: str  # "connected" | "disconnected"
    version: str
    built_by: str
