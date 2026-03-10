from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.quest import Quest
from app.models.world import World
from app.schemas.expedition import (
    ExpeditionExecuteRequest,
    ExpeditionExecuteResponse,
    ExpeditionOptionItem,
    ExpeditionOverviewResponse,
)
from app.services.campaign_phase_service import transition_campaign_phase
from app.services.expedition_service import (
    build_expedition_encounter_hint,
    build_expedition_equipment_support_summary,
    build_expedition_option_suggestions,
    execute_expedition_action,
    get_expedition_context,
    is_expedition_location,
    list_expedition_options,
    serialize_gathered_materials,
)
from app.services.narrative_scene_service import build_campaign_scene_payload
from app.services.world_progress_service import get_or_create_world_state

router = APIRouter(prefix="/api/expedition", tags=["expedition"])


@router.get("/worlds/{world_id}", response_model=ExpeditionOverviewResponse)
def get_expedition_overview(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")
        if not is_expedition_location(world):
            raise HTTPException(status_code=400, detail="Current location does not support expedition")

        transition_campaign_phase(db, world_id=world_id, target_phase="EXPEDITION")
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        context = get_expedition_context(db, world_id=world_id)
        suggestion = build_expedition_option_suggestions(db, world=world)
        return ExpeditionOverviewResponse(
            location=world.current_location,
            **payload,
            danger_level=str(context["danger_level"]),
            encounter_hint=build_expedition_encounter_hint(db, world=world),
            progress_stage=int(context["progress_stage"]),
            supply_pressure=int(context["supply_pressure"]),
            gathered_materials_json=serialize_gathered_materials(context),
            purchased_equipment_json=build_expedition_equipment_support_summary(db, world_id=world_id)[0],
            equipment_support_summary=build_expedition_equipment_support_summary(db, world_id=world_id)[1],
            recommended_option_key=str(suggestion["recommended_option_key"]),
            options=[ExpeditionOptionItem(**item) for item in suggestion["options"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/execute", response_model=ExpeditionExecuteResponse)
def execute_expedition(world_id: int, request: ExpeditionExecuteRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")
        if not is_expedition_location(world):
            raise HTTPException(status_code=400, detail="Current location does not support expedition")

        transition_campaign_phase(db, world_id=world_id, target_phase="EXPEDITION")
        state = get_or_create_world_state(db, world_id)
        main_quest = (
            db.query(Quest)
            .filter(Quest.world_id == world_id, Quest.category == "main")
            .first()
        )
        summary, result_type, context = execute_expedition_action(
            db,
            world=world,
            state=state,
            main_quest=main_quest,
            option_key=request.option_key,
        )
        db.commit()
        db.refresh(world)
        payload = build_campaign_scene_payload(db, world_id)
        suggestion = build_expedition_option_suggestions(db, world=world)
        return ExpeditionExecuteResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            danger_level=str(context["danger_level"]),
            encounter_hint=build_expedition_encounter_hint(db, world=world),
            progress_stage=int(context["progress_stage"]),
            supply_pressure=int(context["supply_pressure"]),
            gathered_materials_json=serialize_gathered_materials(context),
            purchased_equipment_json=build_expedition_equipment_support_summary(db, world_id=world_id)[0],
            equipment_support_summary=build_expedition_equipment_support_summary(db, world_id=world_id)[1],
            recommended_option_key=str(suggestion["recommended_option_key"]),
            **payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
