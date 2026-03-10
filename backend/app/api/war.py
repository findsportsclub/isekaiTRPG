from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.world import World
from app.schemas.war import (
    WarExecuteRequest,
    WarExecuteResponse,
    WarFrontItem,
    WarOverviewResponse,
)
from app.services.campaign_phase_service import transition_campaign_phase
from app.services.narrative_scene_service import build_campaign_scene_payload
from app.services.war_service import (
    build_war_front_suggestions,
    execute_war_action,
    get_war_state_snapshot,
    list_war_fronts,
)
from app.services.world_progress_service import get_or_create_world_state

router = APIRouter(prefix="/api/war", tags=["war"])


@router.get("/worlds/{world_id}", response_model=WarOverviewResponse)
def get_war_overview(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="WAR")
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        snapshot = get_war_state_snapshot(db, world_id=world_id)
        suggestion = build_war_front_suggestions(db, world=world)
        return WarOverviewResponse(
            location=world.current_location,
            **payload,
            war_pressure=int(snapshot["war_pressure"]),
            allied_morale=int(snapshot["allied_morale"]),
            defended_fronts=list(snapshot["defended_fronts"]),
            recommended_front_key=str(suggestion["recommended_front_key"]),
            fronts=[WarFrontItem(**item) for item in suggestion["fronts"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/execute", response_model=WarExecuteResponse)
def execute_war(world_id: int, request: WarExecuteRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="WAR")
        state = get_or_create_world_state(db, world_id)
        summary, result_type, snapshot = execute_war_action(
            db,
            world=world,
            state=state,
            front_key=request.front_key,
        )
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        suggestion = build_war_front_suggestions(db, world=world)
        return WarExecuteResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            war_pressure=int(snapshot["war_pressure"]),
            allied_morale=int(snapshot["allied_morale"]),
            defended_fronts=list(snapshot["defended_fronts"]),
            recommended_front_key=str(suggestion["recommended_front_key"]),
            **payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
