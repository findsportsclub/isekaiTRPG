from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.world import World
from app.schemas.campaign import (
    CampaignPhaseOption,
    CampaignPhaseUpdateRequest,
    CampaignPhaseUpdateResponse,
    CampaignStateResponse,
)
from app.schemas.faction import FactionStateItem
from app.schemas.relation import RelationEdgeSummary, RelationStoryQuestItem
from app.services.campaign_phase_service import (
    transition_campaign_phase,
)
from app.services.campaign_overview_service import (
    build_campaign_phase_options,
    build_phase_context_hints,
)
from app.services.faction_service import list_world_factions
from app.services.narrative_scene_service import build_campaign_scene_payload
from app.services.relation_graph_service import list_top_relation_summaries
from app.services.relation_story_service import list_relation_story_quests

router = APIRouter(prefix="/api/campaign", tags=["campaign"])


@router.get("/worlds/{world_id}/state", response_model=CampaignStateResponse)
def get_campaign_state(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        payload = build_campaign_scene_payload(db, world_id)
        return CampaignStateResponse(
            **payload,
            top_relation_summaries=[
                RelationEdgeSummary(**item)
                for item in list_top_relation_summaries(db, world_id=world_id)
            ],
            relation_story_quests=[
                RelationStoryQuestItem(**item)
                for item in list_relation_story_quests(db, world_id=world_id)
            ],
            faction_states=[
                FactionStateItem(**item) for item in list_world_factions(db, world=world)
            ],
            available_phase_options=[
                CampaignPhaseOption(**item)
                for item in build_campaign_phase_options(db, world=world)
            ],
            phase_context_hints=build_phase_context_hints(db, world=world),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/phase", response_model=CampaignPhaseUpdateResponse)
def update_campaign_phase(world_id: int, request: CampaignPhaseUpdateRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        state, previous_phase = transition_campaign_phase(
            db,
            world_id=world_id,
            target_phase=request.target_phase,
        )
        db.commit()
        db.refresh(state)

        payload = build_campaign_scene_payload(db, world_id)
        return CampaignPhaseUpdateResponse(
            previous_phase=previous_phase,
            **payload,
            top_relation_summaries=[
                RelationEdgeSummary(**item)
                for item in list_top_relation_summaries(db, world_id=world_id)
            ],
            relation_story_quests=[
                RelationStoryQuestItem(**item)
                for item in list_relation_story_quests(db, world_id=world_id)
            ],
            faction_states=[
                FactionStateItem(**item) for item in list_world_factions(db, world=world)
            ],
            phase_context_hints=build_phase_context_hints(db, world=world),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
