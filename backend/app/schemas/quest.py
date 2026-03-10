from pydantic import BaseModel


class QuestItem(BaseModel):
    quest_id: str
    category: str
    title: str
    status: str
    description: str
    progress: int


class QuestListResponse(BaseModel):
    quests: list[QuestItem]