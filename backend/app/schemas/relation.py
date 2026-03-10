from pydantic import BaseModel


class RelationStorySeedItem(BaseModel):
    seed_key: str
    label: str
    summary: str


class RelationEdgeSummary(BaseModel):
    actor_key: str
    target_key: str
    display_name: str
    relation_frame: str
    relation_type: str
    attachment_style: str
    story_heat: float
    trust: float
    affection: float
    loyalty: float
    fear: float
    respect: float
    dependency: float
    resentment: float
    faith: float
    political_value: float
    story_flags: list[str]
    story_seeds: list[RelationStorySeedItem]


class RelationStoryQuestItem(BaseModel):
    quest_id: str
    title: str
    status: str
    progress: int
    summary: str
    source_target_key: str
