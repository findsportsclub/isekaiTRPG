from pydantic import BaseModel
from app.schemas.relation import RelationEdgeSummary, RelationStoryQuestItem


class InvestigationOptionItem(BaseModel):
    option_key: str
    label: str
    summary: str
    recommended: bool = False
    reason: str = ""


class InvestigationListResponse(BaseModel):
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
    relation_edge_summary: RelationEdgeSummary | None = None
    relation_story_quests: list[RelationStoryQuestItem] = []
    recommended_option_key: str
    options: list[InvestigationOptionItem]


class InvestigationExecuteRequest(BaseModel):
    option_key: str = "inspect"


class InvestigationExecuteResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    relation_edge_summary: RelationEdgeSummary | None = None
    relation_story_quests: list[RelationStoryQuestItem] = []
    recommended_option_key: str
