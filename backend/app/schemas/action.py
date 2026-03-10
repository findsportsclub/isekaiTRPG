from pydantic import BaseModel


class ActionItem(BaseModel):
    action_id: str
    label: str


class NearbyNpc(BaseModel):
    npc_id: str
    name: str


class NearbyEvent(BaseModel):
    event_id: str
    title: str


class MoveDestination(BaseModel):
    location_id: str
    label: str


class ActionListResponse(BaseModel):
    location: str
    time_label: str
    actions: list[ActionItem]
    nearby_npcs: list[NearbyNpc]
    nearby_events: list[NearbyEvent]
    move_destinations: list[MoveDestination]


class ActionExecuteRequest(BaseModel):
    action_id: str
    target_location: str | None = None
    target_npc_id: str | None = None
    attitude_tone: str | None = None
    intent_tag: str | None = None


class ActionExecuteResponse(BaseModel):
    summary: str
    result_type: str
