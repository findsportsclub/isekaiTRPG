from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.quest import Quest
from app.models.world import World
from app.schemas.interaction import (
    InteractionExecuteRequest,
    InteractionExecuteResponse,
    InteractionListResponse,
    InteractionTargetItem,
)
from app.schemas.relation import RelationEdgeSummary, RelationStoryQuestItem
from app.services.campaign_phase_service import transition_campaign_phase
from app.services.interaction_service import (
    build_interaction_choice_suggestions,
    build_interaction_relation_summary,
    execute_interaction,
    list_interaction_targets,
)
from app.services.narrative_scene_service import build_campaign_scene_payload
from app.services.relation_story_service import list_relation_story_quests
from app.services.world_progress_service import get_or_create_world_state

router = APIRouter(prefix="/api/interaction", tags=["interaction"])


@router.get("/worlds/{world_id}", response_model=InteractionListResponse)
def get_interaction_overview(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        payload = build_campaign_scene_payload(db, world_id)
        raw_targets = list_interaction_targets(world)
        targets = [InteractionTargetItem(**item) for item in raw_targets]
        choice_suggestions = build_interaction_choice_suggestions(
            db,
            world=world,
            target_key=raw_targets[0]["target_key"] if raw_targets else None,
        )
        relation_summary = (
            build_interaction_relation_summary(
                db,
                world=world,
                target_key=raw_targets[0]["target_key"],
            )
            if raw_targets
            else None
        )
        return InteractionListResponse(
            **payload,
            targets=targets,
            **choice_suggestions,
            relation_edge_summary=RelationEdgeSummary(**relation_summary) if relation_summary else None,
            relation_story_quests=[
                RelationStoryQuestItem(**item)
                for item in list_relation_story_quests(db, world_id=world_id)
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/execute", response_model=InteractionExecuteResponse)
def execute_interaction_action(world_id: int, request: InteractionExecuteRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="INTERACTION")
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

        summary, result_type = execute_interaction(
            db,
            world=world,
            state=state,
            main_quest=main_quest,
            side_quest_001=side_quest_001,
            target_key=request.target_key,
            attitude_tone=request.attitude_tone,
            intent_tag=request.intent_tag,
        )
        db.commit()

        payload = build_campaign_scene_payload(db, world_id)
        choice_suggestions = build_interaction_choice_suggestions(
            db,
            world=world,
            target_key=request.target_key,
        )
        relation_summary = build_interaction_relation_summary(
            db,
            world=world,
            target_key=request.target_key,
        )
        return InteractionExecuteResponse(
            result_type=result_type,
            summary=summary,
            **payload,
            recommended_attitude_tone=str(choice_suggestions["recommended_attitude_tone"]),
            recommended_intent_tag=str(choice_suggestions["recommended_intent_tag"]),
            relation_edge_summary=RelationEdgeSummary(**relation_summary) if relation_summary else None,
            relation_story_quests=[
                RelationStoryQuestItem(**item)
                for item in list_relation_story_quests(db, world_id=world_id)
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
