from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# =========================
# 共通データ構造
# =========================

@dataclass
class EffectDefinition:
    effect_type: str
    effect_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "effect_type": self.effect_type,
            "effect_payload": self.effect_payload,
        }


@dataclass
class SkillDefinition:
    skill_key: str
    name: str
    category: str
    target_type: str

    resource_type: str = "NONE"
    resource_cost: int = 0
    cooldown_turns: int = 0

    hit_formula: str = ""
    power_formula: str = ""

    effect_list: list[EffectDefinition] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)
    ai_hint: dict[str, Any] = field(default_factory=dict)
    flavor_text: str = ""

    generated_by_ai: bool = False
    validation_status: str = "VALID"

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_key": self.skill_key,
            "name": self.name,
            "category": self.category,
            "target_type": self.target_type,
            "resource_type": self.resource_type,
            "resource_cost": self.resource_cost,
            "cooldown_turns": self.cooldown_turns,
            "hit_formula": self.hit_formula,
            "power_formula": self.power_formula,
            "effect_list": [e.to_dict() for e in self.effect_list],
            "tags": self.tags,
            "ai_hint": self.ai_hint,
            "flavor_text": self.flavor_text,
            "generated_by_ai": self.generated_by_ai,
            "validation_status": self.validation_status,
        }


@dataclass
class SpellDefinition:
    spell_key: str
    name: str
    category: str
    target_type: str

    resource_type: str = "MP"
    resource_cost: int = 0
    cooldown_turns: int = 0

    hit_formula: str = ""
    power_formula: str = ""

    effect_list: list[EffectDefinition] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)
    ai_hint: dict[str, Any] = field(default_factory=dict)
    flavor_text: str = ""

    generated_by_ai: bool = False
    validation_status: str = "VALID"

    def to_dict(self) -> dict[str, Any]:
        return {
            "spell_key": self.spell_key,
            "name": self.name,
            "category": self.category,
            "target_type": self.target_type,
            "resource_type": self.resource_type,
            "resource_cost": self.resource_cost,
            "cooldown_turns": self.cooldown_turns,
            "hit_formula": self.hit_formula,
            "power_formula": self.power_formula,
            "effect_list": [e.to_dict() for e in self.effect_list],
            "tags": self.tags,
            "ai_hint": self.ai_hint,
            "flavor_text": self.flavor_text,
            "generated_by_ai": self.generated_by_ai,
            "validation_status": self.validation_status,
        }


RegisteredActionDefinition = SkillDefinition | SpellDefinition


@dataclass
class EquipmentDefinition:
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

    effect_list: list[EffectDefinition] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)
    rarity: str = "COMMON"
    flavor_text: str = ""

    generated_by_ai: bool = False
    validation_status: str = "VALID"

    def to_dict(self) -> dict[str, Any]:
        return {
            "equipment_key": self.equipment_key,
            "name": self.name,
            "slot_type": self.slot_type,
            "atk_bonus": self.atk_bonus,
            "defense_bonus": self.defense_bonus,
            "mag_bonus": self.mag_bonus,
            "res_bonus": self.res_bonus,
            "spd_bonus": self.spd_bonus,
            "hit_bonus": self.hit_bonus,
            "eva_bonus": self.eva_bonus,
            "crit_bonus": self.crit_bonus,
            "effect_list": [e.to_dict() for e in self.effect_list],
            "tags": self.tags,
            "rarity": self.rarity,
            "flavor_text": self.flavor_text,
            "generated_by_ai": self.generated_by_ai,
            "validation_status": self.validation_status,
        }


@dataclass
class BlessingDefinition:
    blessing_key: str
    name: str
    domain: str
    grant_type: str = "passive"
    effect_list: list[EffectDefinition] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    flavor_text: str = ""
    devotion_requirement: str = ""
    drawback_text: str = ""
    generated_by_ai: bool = False
    validation_status: str = "VALID"

    def to_dict(self) -> dict[str, Any]:
        return {
            "blessing_key": self.blessing_key,
            "name": self.name,
            "domain": self.domain,
            "grant_type": self.grant_type,
            "effect_list": [e.to_dict() for e in self.effect_list],
            "tags": self.tags,
            "flavor_text": self.flavor_text,
            "devotion_requirement": self.devotion_requirement,
            "drawback_text": self.drawback_text,
            "generated_by_ai": self.generated_by_ai,
            "validation_status": self.validation_status,
        }


@dataclass
class CheatAuthorityDefinition:
    authority_key: str
    name: str
    authority_class: str
    scope: str
    activation_mode: str = "passive"
    rule_break_level: str = "mid"
    effect_list: list[EffectDefinition] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    flavor_text: str = ""
    continuity_inheritable: bool = True
    generated_by_ai: bool = False
    validation_status: str = "VALID"

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_key": self.authority_key,
            "name": self.name,
            "authority_class": self.authority_class,
            "scope": self.scope,
            "activation_mode": self.activation_mode,
            "rule_break_level": self.rule_break_level,
            "effect_list": [e.to_dict() for e in self.effect_list],
            "tags": self.tags,
            "flavor_text": self.flavor_text,
            "continuity_inheritable": self.continuity_inheritable,
            "generated_by_ai": self.generated_by_ai,
            "validation_status": self.validation_status,
        }


# =========================
# 効果タイプの基準
# =========================

ALLOWED_EFFECT_TYPES = {
    "direct_damage",
    "heal",
    "guard_up",
    "atk_up",
    "def_up",
    "mag_up",
    "res_up",
    "hit_up",
    "eva_up",
    "crit_up",
    "atk_down",
    "def_down",
    "mag_down",
    "res_down",
    "hit_down",
    "eva_down",
    "apply_status",
    "remove_status",
    "forced_move",
    "summon",
    "terrain_change",
    "trigger_gimmick",
    "open_route",
    "restore_mp",
}


# =========================
# 初期登録データ
# スキル / 魔法 / 装備
# =========================

SKILL_REGISTRY: dict[str, SkillDefinition] = {
    "basic_strike": SkillDefinition(
        skill_key="basic_strike",
        name="通常攻撃",
        category="attack",
        target_type="single_enemy",
        resource_type="NONE",
        resource_cost=0,
        cooldown_turns=0,
        hit_formula="basic_physical_hit",
        power_formula="basic_physical_power",
        effect_list=[
            EffectDefinition(
                effect_type="direct_damage",
                effect_payload={
                    "damage_type": "physical",
                    "base": 0,
                    "variance": 2,
                    "crit_multiplier": 1.5,
                },
            )
        ],
        tags=["basic", "physical", "melee"],
        ai_hint={"role_fit": ["front", "striker"], "priority": "default"},
        flavor_text="もっとも基本的な近接攻撃。",
        generated_by_ai=False,
        validation_status="VALID",
    ),
    "guard_stance": SkillDefinition(
        skill_key="guard_stance",
        name="防御",
        category="defense",
        target_type="self",
        resource_type="NONE",
        resource_cost=0,
        cooldown_turns=0,
        hit_formula="",
        power_formula="",
        effect_list=[
            EffectDefinition(
                effect_type="guard_up",
                effect_payload={
                    "multiplier": 1.0,
                    "duration": 1,
                    "tag_multipliers": {"mud_defense": 0.9},
                },
            )
        ],
        tags=["basic", "defense"],
        ai_hint={"role_fit": ["front", "tank", "survivor"], "priority": "situational"},
        flavor_text="姿勢を整え、次の被弾に備える。",
        generated_by_ai=False,
        validation_status="VALID",
    ),
    "quick_feint": SkillDefinition(
        skill_key="quick_feint",
        name="牽制のフェイント",
        category="attack",
        target_type="single_enemy",
        resource_type="NONE",
        resource_cost=0,
        cooldown_turns=1,
        hit_formula="basic_physical_hit",
        power_formula="light_physical_power",
        effect_list=[
            EffectDefinition(
                effect_type="direct_damage",
                effect_payload={
                    "damage_type": "physical",
                    "power_scale": 0.8,
                    "variance": 2,
                    "crit_multiplier": 1.5,
                },
            )
        ],
        tags=["physical", "feint", "tactical"],
        ai_hint={"prefers_tag": "feint_attack", "priority": "opening"},
        flavor_text="相手の反応を誘う軽い攻撃。",
        generated_by_ai=False,
        validation_status="VALID",
    ),
}

SPELL_REGISTRY: dict[str, SpellDefinition] = {
    "minor_heal": SpellDefinition(
        spell_key="minor_heal",
        name="小癒",
        category="recovery",
        target_type="single_ally",
        resource_type="MP",
        resource_cost=4,
        cooldown_turns=0,
        hit_formula="auto",
        power_formula="minor_heal_power",
        effect_list=[
            EffectDefinition(
                effect_type="heal",
                effect_payload={
                    "scale_stat": "mag",
                    "base": 8,
                    "variance_min": 0,
                    "variance_max": 3,
                },
            )
        ],
        tags=["magic", "heal", "support"],
        ai_hint={"role_fit": ["healer", "support"], "hp_threshold": 0.5},
        flavor_text="軽度の傷を癒やす初歩の回復魔法。",
        generated_by_ai=False,
        validation_status="VALID",
    ),
    "ember_shot": SpellDefinition(
        spell_key="ember_shot",
        name="火弾",
        category="offense",
        target_type="single_enemy",
        resource_type="MP",
        resource_cost=5,
        cooldown_turns=0,
        hit_formula="basic_magic_hit",
        power_formula="basic_magic_power",
        effect_list=[
            EffectDefinition(
                effect_type="direct_damage",
                effect_payload={
                    "damage_type": "magic",
                    "element": "fire",
                    "base": 10,
                    "variance": 2,
                    "crit_multiplier": 1.4,
                },
            )
        ],
        tags=["magic", "fire", "ranged"],
        ai_hint={"role_fit": ["mage", "ranged"], "priority": "default"},
        flavor_text="火の魔力を凝縮して放つ基本魔法。",
        generated_by_ai=False,
        validation_status="VALID",
    ),
}

EQUIPMENT_REGISTRY: dict[str, EquipmentDefinition] = {
    "rusty_sword": EquipmentDefinition(
        equipment_key="rusty_sword",
        name="錆びた剣",
        slot_type="weapon",
        atk_bonus=2,
        defense_bonus=0,
        mag_bonus=0,
        res_bonus=0,
        spd_bonus=0,
        hit_bonus=0,
        eva_bonus=0,
        crit_bonus=0,
        effect_list=[],
        tags=["weapon", "sword", "common"],
        rarity="COMMON",
        flavor_text="長く使われ、刃こぼれも目立つ古い剣。",
        generated_by_ai=False,
        validation_status="VALID",
    ),
    "wooden_shield": EquipmentDefinition(
        equipment_key="wooden_shield",
        name="木盾",
        slot_type="offhand",
        atk_bonus=0,
        defense_bonus=2,
        mag_bonus=0,
        res_bonus=0,
        spd_bonus=-1,
        hit_bonus=0,
        eva_bonus=0,
        crit_bonus=0,
        effect_list=[],
        tags=["shield", "defense", "common"],
        rarity="COMMON",
        flavor_text="簡素だが、最低限の防御には使える盾。",
        generated_by_ai=False,
        validation_status="VALID",
    ),
    "apprentice_robe": EquipmentDefinition(
        equipment_key="apprentice_robe",
        name="見習いのローブ",
        slot_type="armor",
        atk_bonus=0,
        defense_bonus=0,
        mag_bonus=2,
        res_bonus=1,
        spd_bonus=0,
        hit_bonus=0,
        eva_bonus=0,
        crit_bonus=0,
        effect_list=[],
        tags=["robe", "magic", "light"],
        rarity="COMMON",
        flavor_text="魔術の初歩を学ぶ者が身にまとう簡素な衣。",
        generated_by_ai=False,
        validation_status="VALID",
    ),
}

BLESSING_REGISTRY: dict[str, BlessingDefinition] = {
    "light_heal_blessing": BlessingDefinition(
        blessing_key="light_heal_blessing",
        name="光癒の恩寵",
        domain="光／回復",
        grant_type="passive",
        effect_list=[
            EffectDefinition(
                effect_type="def_up",
                effect_payload={"base": 1, "duration": 1},
            )
        ],
        tags=["blessing", "light", "heal"],
        flavor_text="穏やかな癒しと守りをもたらす加護。",
        devotion_requirement="祈りと奉仕を重ねること。",
        drawback_text="異端視される土地では働きが鈍る。",
    ),
}

AUTHORITY_REGISTRY: dict[str, CheatAuthorityDefinition] = {
    "continuity_anchor": CheatAuthorityDefinition(
        authority_key="continuity_anchor",
        name="継承固定",
        authority_class="continuity",
        scope="continuity",
        activation_mode="loop_reward",
        rule_break_level="high",
        effect_list=[],
        tags=["authority", "continuity", "inheritance"],
        flavor_text="周回をまたいで痕跡を保持する義認権能。",
        continuity_inheritable=True,
    ),
}


# =========================
# 取得系
# =========================

def list_skills() -> list[SkillDefinition]:
    return list(SKILL_REGISTRY.values())


def list_spells() -> list[SpellDefinition]:
    return list(SPELL_REGISTRY.values())


def list_equipment() -> list[EquipmentDefinition]:
    return list(EQUIPMENT_REGISTRY.values())


def list_blessings() -> list[BlessingDefinition]:
    return list(BLESSING_REGISTRY.values())


def list_authorities() -> list[CheatAuthorityDefinition]:
    return list(AUTHORITY_REGISTRY.values())


def get_skill(skill_key: str) -> SkillDefinition | None:
    return SKILL_REGISTRY.get(skill_key)


def get_spell(spell_key: str) -> SpellDefinition | None:
    return SPELL_REGISTRY.get(spell_key)


def get_equipment(equipment_key: str) -> EquipmentDefinition | None:
    return EQUIPMENT_REGISTRY.get(equipment_key)


def get_blessing(blessing_key: str) -> BlessingDefinition | None:
    return BLESSING_REGISTRY.get(blessing_key)


def get_authority(authority_key: str) -> CheatAuthorityDefinition | None:
    return AUTHORITY_REGISTRY.get(authority_key)


# =========================
# 登録・更新系
# 後で AI生成結果や手動追加を通す入口
# =========================

def validate_effect_definition(effect: EffectDefinition) -> list[str]:
    issues: list[str] = []

    if not effect.effect_type:
        issues.append("effect_type is required")
    elif effect.effect_type not in ALLOWED_EFFECT_TYPES:
        issues.append(f"effect_type '{effect.effect_type}' is not allowed")

    if not isinstance(effect.effect_payload, dict):
        issues.append("effect_payload must be dict")

    return issues


def validate_skill_definition(skill: SkillDefinition) -> list[str]:
    issues: list[str] = []

    if not skill.skill_key:
        issues.append("skill_key is required")
    if not skill.name:
        issues.append("name is required")
    if not skill.category:
        issues.append("category is required")
    if not skill.target_type:
        issues.append("target_type is required")

    if skill.resource_cost < 0:
        issues.append("resource_cost must be >= 0")
    if skill.cooldown_turns < 0:
        issues.append("cooldown_turns must be >= 0")

    for effect in skill.effect_list:
        issues.extend(validate_effect_definition(effect))

    return issues


def validate_spell_definition(spell: SpellDefinition) -> list[str]:
    issues: list[str] = []

    if not spell.spell_key:
        issues.append("spell_key is required")
    if not spell.name:
        issues.append("name is required")
    if not spell.category:
        issues.append("category is required")
    if not spell.target_type:
        issues.append("target_type is required")

    if spell.resource_cost < 0:
        issues.append("resource_cost must be >= 0")
    if spell.cooldown_turns < 0:
        issues.append("cooldown_turns must be >= 0")

    for effect in spell.effect_list:
        issues.extend(validate_effect_definition(effect))

    return issues


def validate_equipment_definition(equipment: EquipmentDefinition) -> list[str]:
    issues: list[str] = []

    if not equipment.equipment_key:
        issues.append("equipment_key is required")
    if not equipment.name:
        issues.append("name is required")
    if not equipment.slot_type:
        issues.append("slot_type is required")

    for effect in equipment.effect_list:
        issues.extend(validate_effect_definition(effect))

    return issues


def validate_blessing_definition(blessing: BlessingDefinition) -> list[str]:
    issues: list[str] = []
    if not blessing.blessing_key:
        issues.append("blessing_key is required")
    if not blessing.name:
        issues.append("name is required")
    if not blessing.domain:
        issues.append("domain is required")
    for effect in blessing.effect_list:
        issues.extend(validate_effect_definition(effect))
    return issues


def validate_authority_definition(authority: CheatAuthorityDefinition) -> list[str]:
    issues: list[str] = []
    if not authority.authority_key:
        issues.append("authority_key is required")
    if not authority.name:
        issues.append("name is required")
    if not authority.authority_class:
        issues.append("authority_class is required")
    if not authority.scope:
        issues.append("scope is required")
    for effect in authority.effect_list:
        issues.extend(validate_effect_definition(effect))
    return issues


def register_skill(skill: SkillDefinition, overwrite: bool = True) -> tuple[bool, list[str]]:
    issues = validate_skill_definition(skill)
    if issues:
        return False, issues

    if not overwrite and skill.skill_key in SKILL_REGISTRY:
        return False, [f"skill_key '{skill.skill_key}' already exists"]

    SKILL_REGISTRY[skill.skill_key] = skill
    return True, []


def register_spell(spell: SpellDefinition, overwrite: bool = True) -> tuple[bool, list[str]]:
    issues = validate_spell_definition(spell)
    if issues:
        return False, issues

    if not overwrite and spell.spell_key in SPELL_REGISTRY:
        return False, [f"spell_key '{spell.spell_key}' already exists"]

    SPELL_REGISTRY[spell.spell_key] = spell
    return True, []


def register_equipment(equipment: EquipmentDefinition, overwrite: bool = True) -> tuple[bool, list[str]]:
    issues = validate_equipment_definition(equipment)
    if issues:
        return False, issues

    if not overwrite and equipment.equipment_key in EQUIPMENT_REGISTRY:
        return False, [f"equipment_key '{equipment.equipment_key}' already exists"]

    EQUIPMENT_REGISTRY[equipment.equipment_key] = equipment
    return True, []


def register_blessing(blessing: BlessingDefinition, overwrite: bool = True) -> tuple[bool, list[str]]:
    issues = validate_blessing_definition(blessing)
    if issues:
        return False, issues
    if not overwrite and blessing.blessing_key in BLESSING_REGISTRY:
        return False, [f"blessing_key '{blessing.blessing_key}' already exists"]
    BLESSING_REGISTRY[blessing.blessing_key] = blessing
    return True, []


def register_authority(authority: CheatAuthorityDefinition, overwrite: bool = True) -> tuple[bool, list[str]]:
    issues = validate_authority_definition(authority)
    if issues:
        return False, issues
    if not overwrite and authority.authority_key in AUTHORITY_REGISTRY:
        return False, [f"authority_key '{authority.authority_key}' already exists"]
    AUTHORITY_REGISTRY[authority.authority_key] = authority
    return True, []


# =========================
# 正規化入口
# AI生成物や手入力を受けるための軽量変換
# =========================

def normalize_effect_payload(raw: dict[str, Any]) -> EffectDefinition:
    return EffectDefinition(
        effect_type=str(raw.get("effect_type", "")).strip(),
        effect_payload=dict(raw.get("effect_payload", {}) or {}),
    )


def normalize_skill_payload(raw: dict[str, Any]) -> SkillDefinition:
    effect_list = [
        normalize_effect_payload(x)
        for x in list(raw.get("effect_list", []) or [])
        if isinstance(x, dict)
    ]

    return SkillDefinition(
        skill_key=str(raw.get("skill_key", "")).strip(),
        name=str(raw.get("name", "")).strip(),
        category=str(raw.get("category", "")).strip(),
        target_type=str(raw.get("target_type", "")).strip(),
        resource_type=str(raw.get("resource_type", "NONE")).strip(),
        resource_cost=int(raw.get("resource_cost", 0) or 0),
        cooldown_turns=int(raw.get("cooldown_turns", 0) or 0),
        hit_formula=str(raw.get("hit_formula", "")).strip(),
        power_formula=str(raw.get("power_formula", "")).strip(),
        effect_list=effect_list,
        tags=[str(x) for x in list(raw.get("tags", []) or [])],
        ai_hint=dict(raw.get("ai_hint", {}) or {}),
        flavor_text=str(raw.get("flavor_text", "")).strip(),
        generated_by_ai=bool(raw.get("generated_by_ai", False)),
        validation_status=str(raw.get("validation_status", "VALID")).strip() or "VALID",
    )


def normalize_spell_payload(raw: dict[str, Any]) -> SpellDefinition:
    effect_list = [
        normalize_effect_payload(x)
        for x in list(raw.get("effect_list", []) or [])
        if isinstance(x, dict)
    ]

    return SpellDefinition(
        spell_key=str(raw.get("spell_key", "")).strip(),
        name=str(raw.get("name", "")).strip(),
        category=str(raw.get("category", "")).strip(),
        target_type=str(raw.get("target_type", "")).strip(),
        resource_type=str(raw.get("resource_type", "MP")).strip(),
        resource_cost=int(raw.get("resource_cost", 0) or 0),
        cooldown_turns=int(raw.get("cooldown_turns", 0) or 0),
        hit_formula=str(raw.get("hit_formula", "")).strip(),
        power_formula=str(raw.get("power_formula", "")).strip(),
        effect_list=effect_list,
        tags=[str(x) for x in list(raw.get("tags", []) or [])],
        ai_hint=dict(raw.get("ai_hint", {}) or {}),
        flavor_text=str(raw.get("flavor_text", "")).strip(),
        generated_by_ai=bool(raw.get("generated_by_ai", False)),
        validation_status=str(raw.get("validation_status", "VALID")).strip() or "VALID",
    )


def normalize_equipment_payload(raw: dict[str, Any]) -> EquipmentDefinition:
    effect_list = [
        normalize_effect_payload(x)
        for x in list(raw.get("effect_list", []) or [])
        if isinstance(x, dict)
    ]

    return EquipmentDefinition(
        equipment_key=str(raw.get("equipment_key", "")).strip(),
        name=str(raw.get("name", "")).strip(),
        slot_type=str(raw.get("slot_type", "")).strip(),
        atk_bonus=int(raw.get("atk_bonus", 0) or 0),
        defense_bonus=int(raw.get("defense_bonus", 0) or 0),
        mag_bonus=int(raw.get("mag_bonus", 0) or 0),
        res_bonus=int(raw.get("res_bonus", 0) or 0),
        spd_bonus=int(raw.get("spd_bonus", 0) or 0),
        hit_bonus=int(raw.get("hit_bonus", 0) or 0),
        eva_bonus=int(raw.get("eva_bonus", 0) or 0),
        crit_bonus=int(raw.get("crit_bonus", 0) or 0),
        effect_list=effect_list,
        tags=[str(x) for x in list(raw.get("tags", []) or [])],
        rarity=str(raw.get("rarity", "COMMON")).strip() or "COMMON",
        flavor_text=str(raw.get("flavor_text", "")).strip(),
        generated_by_ai=bool(raw.get("generated_by_ai", False)),
        validation_status=str(raw.get("validation_status", "VALID")).strip() or "VALID",
    )


# =========================
# 簡易ロードアウト
# 今後、combatant側の ai_profile_key / loadout_key から使う
# =========================

LOADOUT_REGISTRY: dict[str, dict[str, Any]] = {
    "basic_fighter": {
        "skill_keys": ["basic_strike", "guard_stance", "quick_feint"],
        "spell_keys": [],
        "equipment_keys": ["rusty_sword", "wooden_shield"],
    },
    "basic_mage": {
        "skill_keys": ["basic_strike", "guard_stance"],
        "spell_keys": ["minor_heal", "ember_shot"],
        "equipment_keys": ["apprentice_robe"],
    },
    "basic_monster": {
        "skill_keys": ["basic_strike"],
        "spell_keys": [],
        "equipment_keys": [],
    },
}


def get_loadout(loadout_key: str) -> dict[str, Any] | None:
    return LOADOUT_REGISTRY.get(loadout_key)


def get_loadout_skill_keys(loadout_key: str) -> list[str]:
    loadout = get_loadout(loadout_key)
    if not loadout:
        return []
    return list(loadout.get("skill_keys", []) or [])


def get_loadout_spell_keys(loadout_key: str) -> list[str]:
    loadout = get_loadout(loadout_key)
    if not loadout:
        return []
    return list(loadout.get("spell_keys", []) or [])


def get_loadout_equipment_keys(loadout_key: str) -> list[str]:
    loadout = get_loadout(loadout_key)
    if not loadout:
        return []
    return list(loadout.get("equipment_keys", []) or [])


# =========================
# 装備補正集計
# combatant生成時 / 表示時に使える
# =========================

def build_equipment_bonus_summary(equipment_keys: list[str]) -> dict[str, int]:
    summary = {
        "atk_bonus": 0,
        "defense_bonus": 0,
        "mag_bonus": 0,
        "res_bonus": 0,
        "spd_bonus": 0,
        "hit_bonus": 0,
        "eva_bonus": 0,
        "crit_bonus": 0,
    }

    for key in equipment_keys:
        equipment = get_equipment(key)
        if not equipment:
            continue

        summary["atk_bonus"] += equipment.atk_bonus
        summary["defense_bonus"] += equipment.defense_bonus
        summary["mag_bonus"] += equipment.mag_bonus
        summary["res_bonus"] += equipment.res_bonus
        summary["spd_bonus"] += equipment.spd_bonus
        summary["hit_bonus"] += equipment.hit_bonus
        summary["eva_bonus"] += equipment.eva_bonus
        summary["crit_bonus"] += equipment.crit_bonus

    return summary
