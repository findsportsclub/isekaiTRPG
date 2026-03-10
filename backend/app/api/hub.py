from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.world import World
from app.schemas.faction import FactionStateItem
from app.schemas.hub import (
    HubBuyMarketOfferRequest,
    HubBuyMarketOfferResponse,
    HubCraftPreviewItem,
    HubCraftRequest,
    HubCraftResponse,
    HubEconomyPreviewItem,
    HubGambleResponse,
    HubHousingPreviewItem,
    HubHousingUpgradeResponse,
    HubMealResponse,
    HubMarketOfferItem,
    HubMoveDestinationItem,
    HubOverviewResponse,
    HubPartySummaryItem,
    HubRestResponse,
    HubSellPreviewItem,
    HubSellResponse,
    HubTaxResponse,
    HubTravelRequest,
    HubTravelResponse,
)
from app.services.campaign_phase_service import transition_campaign_phase
from app.services.faction_service import list_world_factions
from app.services.hub_service import (
    build_gathering_summary,
    build_economy_snapshot,
    build_hub_resource_summary,
    build_housing_preview,
    execute_hub_buy_market_offer,
    execute_hub_craft,
    execute_hub_gamble,
    execute_hub_upgrade_housing,
    execute_hub_meal,
    execute_hub_pay_tax,
    execute_hub_rest,
    execute_hub_sell_materials,
    execute_hub_travel,
    list_craft_previews,
    list_economy_previews,
    list_hub_move_destinations,
    list_market_offers,
    list_party_progress_summary,
    list_recent_rumors,
    list_sell_previews,
)
from app.services.narrative_scene_service import build_campaign_scene_payload
from app.services.world_progress_service import get_or_create_world_state

router = APIRouter(prefix="/api/hub", tags=["hub"])


@router.get("/worlds/{world_id}", response_model=HubOverviewResponse)
def get_hub_overview(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        state = get_or_create_world_state(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)

        return HubOverviewResponse(
            location=world.current_location,
            **payload,
            available_menu_actions=["rest", "meal", "gamble", "pay_tax", "travel", "prepare_loadout", "review_party", "craft", "sell_materials", "buy_market_offer", "upgrade_housing"],
            move_destinations=[
                HubMoveDestinationItem(**item) for item in list_hub_move_destinations(world)
            ],
            party_summary=[
                HubPartySummaryItem(**item)
                for item in list_party_progress_summary(db, world_id=world_id)
            ],
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
            craft_previews=[
                HubCraftPreviewItem(**item) for item in list_craft_previews(db, world_id=world_id)
            ],
            sell_previews=[
                HubSellPreviewItem(**item) for item in list_sell_previews(db, world_id=world_id)
            ],
            economy_previews=[
                HubEconomyPreviewItem(**item) for item in list_economy_previews(world, state)
            ],
            market_offers=[
                HubMarketOfferItem(**item) for item in list_market_offers(db, world=world, state=state)
            ],
            housing_preview=HubHousingPreviewItem(**build_housing_preview(state)) if build_housing_preview(state) else None,
            faction_states=[
                FactionStateItem(**item) for item in list_world_factions(db, world=world)
            ],
            recent_rumors=list_recent_rumors(db, world_id=world_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/rest", response_model=HubRestResponse)
def execute_hub_rest_action(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        state = get_or_create_world_state(db, world_id)
        summary, result_type = execute_hub_rest(db, world=world, state=state)
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubRestResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/travel", response_model=HubTravelResponse)
def execute_hub_travel_action(world_id: int, request: HubTravelRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        summary, result_type = execute_hub_travel(
            db,
            world=world,
            target_location=request.target_location,
        )
        db.commit()
        db.refresh(world)
        payload = build_campaign_scene_payload(db, world_id)
        state = get_or_create_world_state(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubTravelResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/craft", response_model=HubCraftResponse)
def execute_hub_craft_action(world_id: int, request: HubCraftRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        summary, result_type = execute_hub_craft(db, world=world, recipe_key=request.recipe_key)
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        state = get_or_create_world_state(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubCraftResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/sell-materials", response_model=HubSellResponse)
def execute_hub_sell_action(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        summary, result_type = execute_hub_sell_materials(db, world=world)
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        state = get_or_create_world_state(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubSellResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/meal", response_model=HubMealResponse)
def execute_hub_meal_action(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        state = get_or_create_world_state(db, world_id)
        summary, result_type = execute_hub_meal(db, world=world, state=state)
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubMealResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/gamble", response_model=HubGambleResponse)
def execute_hub_gamble_action(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        state = get_or_create_world_state(db, world_id)
        summary, result_type = execute_hub_gamble(db, world=world, state=state)
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubGambleResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/pay-tax", response_model=HubTaxResponse)
def execute_hub_pay_tax_action(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        state = get_or_create_world_state(db, world_id)
        summary, result_type = execute_hub_pay_tax(db, world=world, state=state)
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubTaxResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/buy-market-offer", response_model=HubBuyMarketOfferResponse)
def execute_hub_buy_market_offer_action(world_id: int, request: HubBuyMarketOfferRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        state = get_or_create_world_state(db, world_id)
        summary, result_type = execute_hub_buy_market_offer(db, world=world, state=state, offer_key=request.offer_key)
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubBuyMarketOfferResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/worlds/{world_id}/upgrade-housing", response_model=HubHousingUpgradeResponse)
def execute_hub_upgrade_housing_action(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        transition_campaign_phase(db, world_id=world_id, target_phase="HUB")
        state = get_or_create_world_state(db, world_id)
        summary, result_type = execute_hub_upgrade_housing(db, world=world, state=state)
        db.commit()
        payload = build_campaign_scene_payload(db, world_id)
        gathered_materials_json, gathering_summary = build_gathering_summary(db, world_id=world_id)
        crafted_supplies_json, material_credit, purchased_equipment_json = build_hub_resource_summary(db, world_id=world_id)
        economy = build_economy_snapshot(state)
        return HubHousingUpgradeResponse(
            location=world.current_location,
            result_type=result_type,
            summary=summary,
            **payload,
            gold=int(economy["gold"]),
            tax_debt=int(economy["tax_debt"]),
            meal_stock=int(economy["meal_stock"]),
            housing_tier=str(economy["housing_tier"]),
            gathered_materials_json=gathered_materials_json,
            gathering_summary=gathering_summary,
            crafted_supplies_json=crafted_supplies_json,
            material_credit=material_credit,
            purchased_equipment_json=purchased_equipment_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
