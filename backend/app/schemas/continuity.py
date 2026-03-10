from pydantic import BaseModel
from app.schemas.faction import FactionStateItem
from app.schemas.relation import RelationEdgeSummary, RelationStoryQuestItem


class ChronicleLogItem(BaseModel):
    log_type: str
    title: str
    body: str


class ChronicleQuestItem(BaseModel):
    quest_id: str
    title: str
    status: str
    progress: int


class InheritanceOptionItem(BaseModel):
    inheritance_key: str
    label: str
    summary: str


class PurchasedEquipmentItem(BaseModel):
    equipment_key: str
    name: str
    slot_type: str
    rarity: str
    summary: str


class BlessingOfferItem(BaseModel):
    blessing_key: str
    name: str
    domain: str
    source_hint: str
    effect_tags: list[str]
    grant_type: str
    summary: str


class AuthorityCandidateItem(BaseModel):
    authority_key: str
    name: str
    authority_class: str
    scope: str
    rule_break_level: str
    summary: str


class ContinuityOverviewResponse(BaseModel):
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
    chronicle_summary: str
    security_score: int
    security_band: str
    security_outlook: str
    gathered_materials_json: str
    materials_legacy_summary: str
    purchased_equipment: list[PurchasedEquipmentItem]
    recent_logs: list[ChronicleLogItem]
    active_quests: list[ChronicleQuestItem]
    inheritance_options: list[InheritanceOptionItem]
    blessing_offers: list[BlessingOfferItem]
    authority_candidates: list[AuthorityCandidateItem]
