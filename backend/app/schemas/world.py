from pydantic import BaseModel


class WorldListItem(BaseModel):
    world_id: int
    world_name: str
    hero_name: str
    era: str
    current_location: str


class WorldListResponse(BaseModel):
    worlds: list[WorldListItem]


class CrisisScores(BaseModel):
    dungeon: int
    faction: int
    demon: int
    security: int


class MainEvent(BaseModel):
    title: str
    state: str
    progress: int


class WorldDetailResponse(BaseModel):
    world_id: int
    world_name: str
    hero_name: str
    era: str
    current_location: str
    crisis_scores: CrisisScores
    main_event: MainEvent
    recent_rumors: list[str]

class WorldCreateRequest(BaseModel):
    user_id: int
    world_name: str
    hero_name: str
    seed: int


class WorldCreateResponse(BaseModel):
    world_id: int
    world_name: str
    hero_name: str
    era: str
    current_location: str
