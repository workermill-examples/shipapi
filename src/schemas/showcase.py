from pydantic import BaseModel, ConfigDict


class ShowcaseStats(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "products": 50,
                "categories": 20,
                "warehouses": 3,
                "stock_alerts": 5,
                "stock_transfers": 30,
                "audit_log_entries": 150,
            }
        }
    )

    products: int
    categories: int
    warehouses: int
    stock_alerts: int
    stock_transfers: int
    audit_log_entries: int
