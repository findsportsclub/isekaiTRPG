from pydantic import BaseModel
from app.schemas.faction import FactionStateItem
from app.schemas.relation import RelationEdgeSummary, RelationStoryQuestItem


class CampaignPhaseOption(BaseModel):
    phase_key: str
    label: str
    summary: str
    route_path: str
    enabled: bool
    recommended: bool
    state_hint: str


class CampaignStateResponse(BaseModel):
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
    top_relation_summaries: list[RelationEdgeSummary]
    relation_story_quests: list[RelationStoryQuestItem]
    faction_states: list[FactionStateItem]
    phase_context_hints: list[str]
    available_phase_options: list[CampaignPhaseOption]


class CampaignPhaseUpdateRequest(BaseModel):
    target_phase: str


class CampaignPhaseUpdateResponse(BaseModel):
    world_id: int
    previous_phase: str
    current_phase: str
    current_phase_label: str
    time_slot: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    top_relation_summaries: list[RelationEdgeSummary]
    relation_story_quests: list[RelationStoryQuestItem]
    faction_states: list[FactionStateItem]
    phase_context_hints: list[str]
