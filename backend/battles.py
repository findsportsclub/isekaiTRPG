from pydantic import BaseModel, Field


# =========================
# 基本レスポンス
# =========================

class BattleCreateResponse(BaseModel):
    battle_id: int
    state: str
    turn_no: int


class CombatantCreateResponse(BaseModel):
    combatant_id: int
    display_name: str
    side: str
    state: str


class BasicAttackResponse(BaseModel):
    declaration_id: int
    resolution_status: str


class BasicDefendResponse(BaseModel):
    declaration_id: int
    resolution_status: str


class AdvanceTurnResponse(BaseModel):
    battle_id: int
    turn_no: int
    state: str
    acted_enemy_count: int


# =========================
# 戦闘作成・参加者追加
# =========================

class CreateBattleRequest(BaseModel):
    world_id: int
    location_id: str = "test_field"
    battle_type: str = "ENCOUNTER"
    source_type: str = "MANUAL"
    source_ref_id: str = "manual_battle"
    battlefield_id: int | None = None
    objective_type: str = "DEFEAT"


class CreateCombatantRequest(BaseModel):
    battle_id: int

    entity_type: str
    entity_id: str
    display_name: str

    side: str
    role: str = "FRONT"

    hp_current: int
    hp_max: int
    mp_current: int = 0
    mp_max: int = 0

    atk: int = 1
    defense: int = 0
    mag: int = 0
    res: int = 0
    spd: int = 1
    hit: int = 0
    eva: int = 0
    crit: int = 0
    guard_rate: int = 0

    is_player_controlled: bool = False

    # 将来用: AIプロファイルや登録型データのキー
    ai_profile_key: str = ""
    loadout_key: str = ""
    notes_json: str = "{}"


# =========================
# 行動リクエスト
# =========================

class BasicAttackRequest(BaseModel):
    battle_id: int
    turn_no: int
    actor_combatant_id: int
    target_combatant_id: int
    declared_tactic_text: str = ""
    risk_level: str = "LOW"


class BasicDefendRequest(BaseModel):
    battle_id: int
    turn_no: int
    actor_combatant_id: int
    declared_tactic_text: str = ""
    risk_level: str = "LOW"


class AdvanceTurnRequest(BaseModel):
    battle_id: int


# =========================
# AI命令・方針
# =========================

class CompanionOrderRequest(BaseModel):
    battle_id: int
    target_combatant_id: int
    order_text: str = ""
    priority: str = "NORMAL"


class CompanionOrderResponse(BaseModel):
    battle_id: int
    target_combatant_id: int
    order_text: str
    priority: str
    accepted: bool


# =========================
# AIプロファイル可視化用
# =========================

class CombatAiProfileResponse(BaseModel):
    profile_key: str = ""
    controller_type: str = ""
    combat_role: str = ""
    behavior_mode: str = ""

    base_traits_json: str = "{}"
    dynamic_traits_json: str = "{}"
    growth_stats_json: str = "{}"
    relationship_modifiers_json: str = "{}"
    temporary_state_tags_json: str = "[]"

    combat_experience: str = "LOW"
    tactical_judgment: str = "LOW"
    command_obedience: float = 0.5
    command_comprehension: float = 0.5
    teamwork_skill: float = 0.5
    morale: float = 0.5
    panic_action_rate: float = 0.0
    hesitation_rate: float = 0.0
    misplay_tendency: float = 0.0

    communication_method: str = "VOICE"
    noise_tolerance: float = 0.5
    requires_line_of_sight_for_command: bool = True

    current_order_text: str = ""
    current_order_priority: str = "NORMAL"


# =========================
# 戦闘詳細
# =========================

class BattleCombatantResponse(BaseModel):
    combatant_id: int
    display_name: str
    side: str
    role: str

    hp_current: int
    hp_max: int
    mp_current: int
    mp_max: int

    state: str

    defend_active: bool
    defend_used_tags_json: str

    has_acted_this_turn: bool = False

    # 将来の距離・位置取り
    range_band: str = "MID"
    position_tags_json: str = "[]"

    # AI関連
    controller_type: str = "PLAYER"
    ai_profile_key: str = ""
    current_order_text: str = ""

    # 行動候補可視化の入口
    available_skill_keys_json: str = "[]"
    available_spell_keys_json: str = "[]"
    equipped_item_keys_json: str = "[]"


class BattleDetailResponse(BaseModel):
    battle_id: int
    world_id: int
    location_id: str
    battlefield_id: int | None

    battle_type: str
    source_type: str
    state: str
    turn_no: int
    objective_type: str

    combatants: list[BattleCombatantResponse]


# =========================
# 行動順
# =========================

class TurnOrderItem(BaseModel):
    combatant_id: int
    display_name: str
    side: str
    spd: int
    state: str
    has_acted: bool


class BattleTurnOrderResponse(BaseModel):
    battle_id: int
    turn_no: int
    order: list[TurnOrderItem]


# =========================
# 戦闘ログ
# =========================

class BattleActionLogResponse(BaseModel):
    action_log_id: int
    turn_no: int

    declaration_id: int | None

    actor_combatant_id: int
    actor_name: str

    target_combatant_id: int | None
    target_name: str | None

    result_type: str

    hit_success: bool
    crit_success: bool
    guard_success: bool
    evade_success: bool

    damage_value: int
    hp_after: int

    declared_tactic_text: str
    used_tags_json: str
    narrative_result: str

    ai_reason_summary: str = ""
    order_applied_text: str = ""


# =========================
# スキル / 魔法 / 装備の登録型基盤
# 今回は schema だけ先に定義
# =========================

class RegisteredEffectResponse(BaseModel):
    effect_type: str
    effect_payload_json: str


class SkillDefinitionResponse(BaseModel):
    skill_key: str
    name: str
    category: str
    target_type: str

    resource_type: str = "NONE"
    resource_cost: int = 0
    cooldown_turns: int = 0

    hit_formula: str = ""
    power_formula: str = ""
    effect_list: list[RegisteredEffectResponse] = Field(default_factory=list)

    tags_json: str = "[]"
    ai_hint_json: str = "{}"
    flavor_text: str = ""

    generated_by_ai: bool = False
    validation_status: str = "VALID"


class SpellDefinitionResponse(BaseModel):
    spell_key: str
    name: str
    category: str
    target_type: str

    resource_type: str = "MP"
    resource_cost: int = 0
    cooldown_turns: int = 0

    hit_formula: str = ""
    power_formula: str = ""
    effect_list: list[RegisteredEffectResponse] = Field(default_factory=list)

    tags_json: str = "[]"
    ai_hint_json: str = "{}"
    flavor_text: str = ""

    generated_by_ai: bool = False
    validation_status: str = "VALID"


class EquipmentDefinitionResponse(BaseModel):
    equipment_key: str
    name: str
    slot_type: str

    atk_bonus: int = 0
    defense_bonus: int = 0
    mag_bonus: int = 0
    res_bonus: int = 0
    spd_bonus: int = 0
    hit_bonus: int = 0
    eva_bonus: int = 0
    crit_bonus: int = 0

    effect_list: list[RegisteredEffectResponse] = Field(default_factory=list)

    tags_json: str = "[]"
    rarity: str = "COMMON"
    flavor_text: str = ""

    generated_by_ai: bool = False
    validation_status: str = "VALID"


# =========================
# AI候補・整合性チェックの入口
# =========================

class GeneratedContentValidationResponse(BaseModel):
    content_key: str
    content_type: str
    is_valid: bool
    normalized_payload_json: str = "{}"
    issues_json: str = "[]"


# =========================
# ネームド敵 / 味方NPC のAI判断可視化
# =========================

class CombatDecisionPreviewResponse(BaseModel):
    combatant_id: int
    display_name: str
    controller_type: str

    selected_action_type: str
    selected_target_id: int | None = None
    selected_tactic_text: str = ""

    reason_summary: str = ""
    order_received_text: str = ""
    order_understood: bool = False
    order_obeyed: bool = False

    panic_modified: bool = False
    misplay_triggered: bool = False
    communication_blocked: bool = False