from pydantic import BaseModel


class LogItem(BaseModel):
    log_id: int
    log_type: str
    title: str
    body: str


class LogListResponse(BaseModel):
    logs: list[LogItem]