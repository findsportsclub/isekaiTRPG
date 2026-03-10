from pydantic import BaseModel


class FactionStateItem(BaseModel):
    faction_key: str
    display_name: str
    category: str
    influence_score: float
    power_score: float
    cohesion_score: float
    tension_score: float
    stance_label: str
    incident_hint: str
