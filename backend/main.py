from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db.session import engine, Base, SessionLocal
import app.models
from app.models.user import User
from app.models.world import World
from app.models.log import Log
from app.models.world_state import WorldState
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.world import (
    WorldListItem,
    WorldListResponse,
    WorldDetailResponse,
    CrisisScores,
    MainEvent,
    WorldCreateRequest,
    WorldCreateResponse,
)
from app.schemas.action import (
    ActionListResponse,
    ActionItem,
    NearbyNpc,
    NearbyEvent,
    MoveDestination,
    ActionExecuteRequest,
    ActionExecuteResponse,
)
from app.schemas.log import LogItem, LogListResponse
from app.schemas.quest import QuestItem, QuestListResponse
from app.models.quest import Quest
from app.models.battle_instance import BattleInstance
from app.models.battle_combatant import BattleCombatant
from app.schemas.battle import (
    CreateBattleRequest,
    BattleCreateResponse,
    BattleCombatantResponse,
    BattleDetailResponse,
    CreateCombatantRequest,
    CombatantCreateResponse,
    BasicAttackRequest,
    BasicAttackResponse,
    BattleActionLogResponse,
    BasicDefendRequest,
    BasicDefendResponse,
)
from app.services.simple_battle_resolver import (
    resolve_basic_attack,
    resolve_basic_defend,
)
from app.models.battle_action_log import BattleActionLog
import json
from app.api.battles import router as battles_router
from app.api.worlds import router as worlds_router
from app.api.campaign import router as campaign_router
from app.api.interaction import router as interaction_router
from app.api.investigation import router as investigation_router
from app.api.hub import router as hub_router
from app.api.expedition import router as expedition_router
from app.api.continuity import router as continuity_router
from app.api.war import router as war_router

def _safe_load_json_dict(json_text: str) -> dict:
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(worlds_router)
app.include_router(battles_router)
app.include_router(campaign_router)
app.include_router(interaction_router)
app.include_router(investigation_router)
app.include_router(hub_router)
app.include_router(expedition_router)
app.include_router(continuity_router)
app.include_router(war_router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}
