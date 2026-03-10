from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.quest import Quest
from app.models.world import World
from app.schemas.investigation import (
    InvestigationExecuteRequest,
    InvestigationExecuteResponse,
    InvestigationListResponse,
    InvestigationOptionItem,
)
from app.schemas.relation import RelationEdgeSummary, RelationStoryQuestItem
from app.services.campaign_phase_service import transition_campaign_phase
from app.services.investigation_service import (
    build_investigation_option_suggestions,
    build_investigation_relation_summary,
    execute_investigation,
    list_investigation_options,
)
from app.services.narrative_scene_service import build_campaign_scene_payload
from app.services.relation_story_service import list_relation_story_quests
from app.services.world_progress_service import get_or_create_world_state

router = APIRouter(prefix="/api/investigation", tags=["investigation"])


@router.get("/worlds/{world_id}", response_model=InvestigationListResponse)
def get_investigation_overview(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        payload = build_campaign_scene_payload(db, world_id)
        state = get_or_create_world_state(db, world_id)
        suggestion = build_investigation_option_suggestions(db, world=world, state=state)
        options = [InvestigationOptionItem(**item) for item in suggestion["options"]]
        relation_summary = build_investigation_relation_summary(db, world=world, state=state)
        return InvestigationListResponse(
            location=world.current_location,
            **payload,
            relation_edge_summary=RelationEdgeSummary(**relation_summary) if relation_summary else None,
            relation_story_quests=[
                RelationStoryQuestItem(**item)
                for item in list_relation_story_quests(db, world_id=world_id)
            ],
            recommended_option_key=str(suggestion["recommended_option_key"]),
            options=options,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/execute", response_model=InvestigationExecuteResponse)
def execute_investigation_action(world_id: int, request: InvestigationExecuteRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="INVESTIGATION")
        state = get_or_create_world_state(db, world_id)
        main_quest = (
            db.query(Quest)
            .filter(Quest.world_id == world_id, Quest.category == "main")
            .first()
        )
        side_quest_001 = (
            db.query(Quest)
            .filter(Quest.world_id == world_id, Quest.quest_id == "side_001")
            .first()
        )

        summary, result_type = execute_investigation(
            db,
            world=world,
            state=state,
            main_quest=main_quest,
            side_quest_001=side_quest_001,
            option_key=request.option_key,
        )
        db.commit()

        payload = build_campaign_scene_payload(db, world_id)
        suggestion = build_investigation_option_suggestions(db, world=world, state=state)
        relation_summary = build_investigation_relation_summary(db, world=world, state=state)
        return InvestigationExecuteResponse(
            result_type=result_type,
            summary=summary,
            **payload,
            relation_edge_summary=RelationEdgeSummary(**relation_summary) if relation_summary else None,
            relation_story_quests=[
                RelationStoryQuestItem(**item)
                for item in list_relation_story_quests(db, world_id=world_id)
            ],
            recommended_option_key=str(suggestion["recommended_option_key"]),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
