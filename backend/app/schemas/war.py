from pydantic import BaseModel


class WarFrontItem(BaseModel):
    front_key: str
    label: str
    pressure: int
    summary: str
    recommended: bool = False
    reason: str = ""


class WarOverviewResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    war_pressure: int
    allied_morale: int
    defended_fronts: list[str]
    recommended_front_key: str
    fronts: list[WarFrontItem]


class WarExecuteRequest(BaseModel):
    front_key: str


class WarExecuteResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    war_pressure: int
    allied_morale: int
    defended_fronts: list[str]
    recommended_front_key: str
