from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.world import World
from app.schemas.continuity import (
    AuthorityCandidateItem,
    BlessingOfferItem,
    ChronicleLogItem,
    ChronicleQuestItem,
    ContinuityOverviewResponse,
    InheritanceOptionItem,
    PurchasedEquipmentItem,
)
from app.schemas.deity import DeitySummaryItem
from app.schemas.faction import FactionStateItem
from app.schemas.relation import RelationEdgeSummary, RelationStoryQuestItem
from app.services.campaign_phase_service import transition_campaign_phase
from app.services.continuity_service import (
    build_authority_candidate_summary,
    build_blessing_offer_summary,
    build_chronicle_summary,
    build_deity_summary,
    build_faction_summary,
    build_inheritance_options,
    build_materials_legacy_summary,
    build_purchased_equipment_legacy_summary,
    build_religious_outlook,
    build_relation_legacy_summary,
    build_relation_story_quest_summary,
    build_security_outlook,
    list_active_quests,
    list_recent_chronicle_logs,
)
from app.services.narrative_scene_service import build_campaign_scene_payload

router = APIRouter(prefix="/api/continuity", tags=["continuity"])


@router.get("/worlds/{world_id}", response_model=ContinuityOverviewResponse)
def get_continuity_overview(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="WORLD")
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        gathered_materials_json, materials_legacy_summary = build_materials_legacy_summary(
            db,
            world=world,
        )
        security_score, security_band, security_outlook = build_security_outlook(db, world=world)
        return ContinuityOverviewResponse(
            **payload,
            top_relation_summaries=[
                RelationEdgeSummary(**item)
                for item in build_relation_legacy_summary(db, world=world)
            ],
            relation_story_quests=[
                RelationStoryQuestItem(**item)
                for item in build_relation_story_quest_summary(db, world=world)
            ],
            faction_states=[
                FactionStateItem(**item)
                for item in build_faction_summary(db, world=world)
            ],
            deities=[
                DeitySummaryItem(**item)
                for item in build_deity_summary(db, world=world)
            ],
            chronicle_summary=build_chronicle_summary(db, world=world),
            religious_outlook=build_religious_outlook(db, world=world),
            security_score=security_score,
            security_band=security_band,
            security_outlook=security_outlook,
            gathered_materials_json=gathered_materials_json,
            materials_legacy_summary=materials_legacy_summary,
            purchased_equipment=[
                PurchasedEquipmentItem(**item)
                for item in build_purchased_equipment_legacy_summary(db, world=world)
            ],
            recent_logs=[
                ChronicleLogItem(**item)
                for item in list_recent_chronicle_logs(db, world_id=world_id)
            ],
            active_quests=[
                ChronicleQuestItem(**item)
                for item in list_active_quests(db, world_id=world_id)
            ],
            inheritance_options=[
                InheritanceOptionItem(**item)
                for item in build_inheritance_options(db, world=world)
            ],
            blessing_offers=[
                BlessingOfferItem(**item)
                for item in build_blessing_offer_summary(db, world=world)
            ],
            authority_candidates=[
                AuthorityCandidateItem(**item)
                for item in build_authority_candidate_summary(db, world=world)
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
