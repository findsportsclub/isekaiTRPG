from pydantic import BaseModel


class ExpeditionOptionItem(BaseModel):
    option_key: str
    label: str
    summary: str
    recommended: bool = False
    reason: str = ""


class ExpeditionOverviewResponse(BaseModel):
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
    danger_level: str
    encounter_hint: str
    progress_stage: int
    supply_pressure: int
    gathered_materials_json: str
    purchased_equipment_json: str
    equipment_support_summary: str
    recommended_option_key: str
    options: list[ExpeditionOptionItem]


class ExpeditionExecuteRequest(BaseModel):
    option_key: str


class ExpeditionExecuteResponse(BaseModel):
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
    danger_level: str
    encounter_hint: str
    progress_stage: int
    supply_pressure: int
    gathered_materials_json: str
    purchased_equipment_json: str
    equipment_support_summary: str
    recommended_option_key: str
