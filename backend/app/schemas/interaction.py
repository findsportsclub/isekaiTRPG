from pydantic import BaseModel
from app.schemas.relation import RelationEdgeSummary, RelationStoryQuestItem


class InteractionTargetItem(BaseModel):
    target_key: str
    display_name: str
    summary: str


class InteractionChoiceSuggestion(BaseModel):
    value: str
    label: str
    recommended: bool
    reason: str


class InteractionListResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    targets: list[InteractionTargetItem]
    attitude_tone_options: list[InteractionChoiceSuggestion]
    intent_tag_options: list[InteractionChoiceSuggestion]
    recommended_attitude_tone: str
    recommended_intent_tag: str
    relation_edge_summary: RelationEdgeSummary | None = None
    relation_story_quests: list[RelationStoryQuestItem] = []


class InteractionExecuteRequest(BaseModel):
    target_key: str
    attitude_tone: str | None = None
    intent_tag: str | None = None


class InteractionExecuteResponse(BaseModel):
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
    recommended_attitude_tone: str
    recommended_intent_tag: str
    relation_edge_summary: RelationEdgeSummary | None = None
    relation_story_quests: list[RelationStoryQuestItem] = []
