from pydantic import BaseModel


class DeitySummaryItem(BaseModel):
    deity_key: str
    name: str
    domains: list[str]
    symbol_mark: str
    doctrine_summary: str
    myth_fragment: str
    church_name: str
    rivalry_hint: str
