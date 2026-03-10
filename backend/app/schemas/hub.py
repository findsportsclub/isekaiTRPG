from pydantic import BaseModel
from app.schemas.faction import FactionStateItem


class HubMoveDestinationItem(BaseModel):
    location_id: str
    label: str
    summary: str


class HubPartySummaryItem(BaseModel):
    entity_id: str
    display_name: str
    growth_summary: str
    relationship_summary: str


class HubCraftPreviewItem(BaseModel):
    recipe_key: str
    label: str
    summary: str
    craftable: bool
    cost_summary: str


class HubSellPreviewItem(BaseModel):
    material_key: str
    label: str
    quantity: int
    estimated_credit: int


class HubEconomyPreviewItem(BaseModel):
    action_key: str
    label: str
    estimated_cost: int
    summary: str


class HubMarketOfferItem(BaseModel):
    offer_key: str
    equipment_key: str
    name: str
    slot_type: str
    rarity: str
    price_gold: int
    main_effect: str
    sub_effect: str
    flavor_text: str
    purchased: bool


class HubHousingPreviewItem(BaseModel):
    housing_tier: str
    next_housing_tier: str
    upgrade_cost: int
    available: bool
    summary: str


class HubOverviewResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    available_menu_actions: list[str]
    move_destinations: list[HubMoveDestinationItem]
    party_summary: list[HubPartySummaryItem]
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str
    craft_previews: list[HubCraftPreviewItem]
    sell_previews: list[HubSellPreviewItem]
    economy_previews: list[HubEconomyPreviewItem]
    market_offers: list[HubMarketOfferItem]
    housing_preview: HubHousingPreviewItem | None = None
    faction_states: list[FactionStateItem]
    recent_rumors: list[str]


class HubRestResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int


class HubCraftRequest(BaseModel):
    recipe_key: str


class HubBuyMarketOfferRequest(BaseModel):
    offer_key: str


class HubCraftResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str


class HubSellResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str


class HubTravelRequest(BaseModel):
    target_location: str


class HubTravelResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str


class HubMealResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str


class HubGambleResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str


class HubTaxResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str


class HubBuyMarketOfferResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str


class HubHousingUpgradeResponse(BaseModel):
    world_id: int
    current_phase: str
    current_phase_label: str
    day_no: int
    time_slot: str
    location: str
    result_type: str
    summary: str
    scene_title: str
    scene_body: str
    tone: str
    weight: str
    protagonist_tendency_hints: list[str]
    active_relationship_hints_json: str
    gold: int
    tax_debt: int
    meal_stock: int
    housing_tier: str
    gathered_materials_json: str
    gathering_summary: str
    crafted_supplies_json: str
    material_credit: int
    purchased_equipment_json: str
