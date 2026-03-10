from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.battle_combatant import BattleCombatant
from app.models.battle_instance import BattleInstance
from app.models.world_combatant_progress import WorldCombatantProgress
from app.services.named_ai_service import decide_named_or_unique_action

# =========================
# 共通ユーティリティ
# =========================

def _safe_load_json_dict(json_text: str) -> dict[str, Any]:
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _safe_load_json_list(json_text: str) -> list[Any]:
    try:
        data = json.loads(json_text)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _write_snapshot(combatant: BattleCombatant, key: str, value: Any) -> None:
    snapshot = _safe_load_json_dict(combatant.snapshot_json)
    snapshot[key] = value
    combatant.snapshot_json = json.dumps(snapshot, ensure_ascii=False)


def _read_snapshot(combatant: BattleCombatant, key: str, default=None):
    snapshot = _safe_load_json_dict(combatant.snapshot_json)
    return snapshot.get(key, default)


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


# =========================
# AIプロファイル
# =========================

@dataclass
class CombatAiProfile:
    profile_key: str
    controller_type: str
    combat_role: str
    behavior_mode: str

    base_traits: dict[str, Any]
    dynamic_traits: dict[str, Any]
    growth_stats: dict[str, Any]
    relationship_modifiers: dict[str, Any]
    temporary_state_tags: list[str]

    combat_experience: str
    tactical_judgment: str
    command_obedience: float
    command_comprehension: float
    teamwork_skill: float
    morale: float
    panic_action_rate: float
    hesitation_rate: float
    misplay_tendency: float

    communication_method: str
    noise_tolerance: float
    requires_line_of_sight_for_command: bool

    current_order_text: str
    current_order_priority: str


@dataclass
class AiDecision:
    selected_action_type: str
    selected_target_id: int | None
    selected_tactic_text: str

    reason_summary: str
    order_received_text: str
    order_understood: bool
    order_obeyed: bool

    panic_modified: bool
    misplay_triggered: bool
    communication_blocked: bool


# =========================
# プロファイル初期値
# ここは後で relation / quest / growth で変化可能
# =========================

AI_PROFILE_REGISTRY: dict[str, dict[str, Any]] = {
    "player_manual": {
        "profile_key": "player_manual",
        "controller_type": "PLAYER",
        "combat_role": "front",
        "behavior_mode": "manual",
        "base_traits": {},
        "dynamic_traits": {},
        "growth_stats": {},
        "relationship_modifiers": {},
        "temporary_state_tags": [],
        "combat_experience": "TRAINED",
        "tactical_judgment": "MEDIUM",
        "command_obedience": 1.0,
        "command_comprehension": 1.0,
        "teamwork_skill": 0.8,
        "morale": 0.8,
        "panic_action_rate": 0.0,
        "hesitation_rate": 0.0,
        "misplay_tendency": 0.0,
        "communication_method": "VOICE",
        "noise_tolerance": 0.7,
        "requires_line_of_sight_for_command": False,
        "current_order_text": "",
        "current_order_priority": "NORMAL",
    },
    "mob_basic_melee": {
        "profile_key": "mob_basic_melee",
        "controller_type": "MOB_AI",
        "combat_role": "front",
        "behavior_mode": "aggressive",
        "base_traits": {"feral": True},
        "dynamic_traits": {},
        "growth_stats": {},
        "relationship_modifiers": {},
        "temporary_state_tags": [],
        "combat_experience": "LOW",
        "tactical_judgment": "LOW",
        "command_obedience": 0.0,
        "command_comprehension": 0.0,
        "teamwork_skill": 0.2,
        "morale": 0.7,
        "panic_action_rate": 0.05,
        "hesitation_rate": 0.05,
        "misplay_tendency": 0.15,
        "communication_method": "INSTINCT",
        "noise_tolerance": 1.0,
        "requires_line_of_sight_for_command": False,
        "current_order_text": "",
        "current_order_priority": "NORMAL",
    },
    "villager_untrained": {
        "profile_key": "villager_untrained",
        "controller_type": "ALLY_AI",
        "combat_role": "civilian",
        "behavior_mode": "fearful",
        "base_traits": {"civilian": True, "timid": True},
        "dynamic_traits": {},
        "growth_stats": {"battle_exp_points": 0},
        "relationship_modifiers": {"trust_in_leader": 0.2},
        "temporary_state_tags": [],
        "combat_experience": "NONE",
        "tactical_judgment": "LOW",
        "command_obedience": 0.55,
        "command_comprehension": 0.35,
        "teamwork_skill": 0.2,
        "morale": 0.3,
        "panic_action_rate": 0.35,
        "hesitation_rate": 0.30,
        "misplay_tendency": 0.45,
        "communication_method": "VOICE",
        "noise_tolerance": 0.2,
        "requires_line_of_sight_for_command": True,
        "current_order_text": "",
        "current_order_priority": "NORMAL",
    },
    "ally_guard_novice": {
        "profile_key": "ally_guard_novice",
        "controller_type": "ALLY_AI",
        "combat_role": "guard",
        "behavior_mode": "protective",
        "base_traits": {"dutiful": True},
        "dynamic_traits": {},
        "growth_stats": {"battle_exp_points": 10},
        "relationship_modifiers": {"trust_in_leader": 0.5},
        "temporary_state_tags": [],
        "combat_experience": "LOW",
        "tactical_judgment": "LOW",
        "command_obedience": 0.75,
        "command_comprehension": 0.65,
        "teamwork_skill": 0.45,
        "morale": 0.6,
        "panic_action_rate": 0.12,
        "hesitation_rate": 0.08,
        "misplay_tendency": 0.20,
        "communication_method": "VOICE",
        "noise_tolerance": 0.45,
        "requires_line_of_sight_for_command": True,
        "current_order_text": "",
        "current_order_priority": "NORMAL",
    },
    "ally_healer_cautious": {
        "profile_key": "ally_healer_cautious",
        "controller_type": "ALLY_AI",
        "combat_role": "healer",
        "behavior_mode": "supportive",
        "base_traits": {"cautious": True, "kind": True},
        "dynamic_traits": {},
        "growth_stats": {"battle_exp_points": 20},
        "relationship_modifiers": {"trust_in_leader": 0.65},
        "temporary_state_tags": [],
        "combat_experience": "TRAINED",
        "tactical_judgment": "MEDIUM",
        "command_obedience": 0.80,
        "command_comprehension": 0.80,
        "teamwork_skill": 0.7,
        "morale": 0.7,
        "panic_action_rate": 0.06,
        "hesitation_rate": 0.10,
        "misplay_tendency": 0.08,
        "communication_method": "VOICE",
        "noise_tolerance": 0.55,
        "requires_line_of_sight_for_command": False,
        "current_order_text": "",
        "current_order_priority": "NORMAL",
    },
    "named_enemy_cold_tactician": {
        "profile_key": "named_enemy_cold_tactician",
        "controller_type": "NAMED_AI",
        "combat_role": "commander",
        "behavior_mode": "calculated",
        "base_traits": {"cold": True, "disciplined": True},
        "dynamic_traits": {},
        "growth_stats": {"battle_exp_points": 100},
        "relationship_modifiers": {},
        "temporary_state_tags": [],
        "combat_experience": "VETERAN",
        "tactical_judgment": "HIGH",
        "command_obedience": 0.0,
        "command_comprehension": 1.0,
        "teamwork_skill": 0.9,
        "morale": 0.85,
        "panic_action_rate": 0.01,
        "hesitation_rate": 0.01,
        "misplay_tendency": 0.03,
        "communication_method": "VOICE",
        "noise_tolerance": 0.8,
        "requires_line_of_sight_for_command": False,
        "current_order_text": "",
        "current_order_priority": "NORMAL",
    },
    "unique_ally_field_captain": {
        "profile_key": "unique_ally_field_captain",
        "controller_type": "ALLY_AI",
        "combat_role": "commander",
        "behavior_mode": "calculated",
        "base_traits": {"unique": True, "disciplined": True, "protective": True},
        "dynamic_traits": {},
        "growth_stats": {"battle_exp_points": 80},
        "relationship_modifiers": {"trust_in_leader": 0.75},
        "temporary_state_tags": [],
        "combat_experience": "VETERAN",
        "tactical_judgment": "HIGH",
        "command_obedience": 0.7,
        "command_comprehension": 0.9,
        "teamwork_skill": 0.9,
        "morale": 0.8,
        "panic_action_rate": 0.02,
        "hesitation_rate": 0.03,
        "misplay_tendency": 0.04,
        "communication_method": "VOICE",
        "noise_tolerance": 0.75,
        "requires_line_of_sight_for_command": False,
        "current_order_text": "",
        "current_order_priority": "NORMAL",
    },
}


# =========================
# プロファイル取得・更新
# =========================

def get_ai_profile_dict(profile_key: str) -> dict[str, Any]:
    return AI_PROFILE_REGISTRY.get(profile_key, AI_PROFILE_REGISTRY["mob_basic_melee"]).copy()


def build_ai_profile_for_combatant(combatant: BattleCombatant) -> CombatAiProfile:
    base = get_ai_profile_dict(_read_snapshot(combatant, "ai_profile_key", "mob_basic_melee"))

    # snapshot 側に変動値があれば優先
    dynamic_traits = _read_snapshot(combatant, "dynamic_traits", base.get("dynamic_traits", {}))
    growth_stats = _read_snapshot(combatant, "growth_stats", base.get("growth_stats", {}))
    relationship_modifiers = _read_snapshot(
        combatant,
        "relationship_modifiers",
        base.get("relationship_modifiers", {}),
    )
    temporary_state_tags = _read_snapshot(
        combatant,
        "temporary_state_tags",
        base.get("temporary_state_tags", []),
    )

    current_order_text = _read_snapshot(
        combatant,
        "current_order_text",
        base.get("current_order_text", ""),
    )
    current_order_priority = _read_snapshot(
        combatant,
        "current_order_priority",
        base.get("current_order_priority", "NORMAL"),
    )

    return CombatAiProfile(
        profile_key=str(base.get("profile_key", "")),
        controller_type=str(base.get("controller_type", "MOB_AI")),
        combat_role=str(base.get("combat_role", "front")),
        behavior_mode=str(base.get("behavior_mode", "aggressive")),
        base_traits=dict(base.get("base_traits", {}) or {}),
        dynamic_traits=dict(dynamic_traits or {}),
        growth_stats=dict(growth_stats or {}),
        relationship_modifiers=dict(relationship_modifiers or {}),
        temporary_state_tags=list(temporary_state_tags or []),
        combat_experience=str(base.get("combat_experience", "LOW")),
        tactical_judgment=str(base.get("tactical_judgment", "LOW")),
        command_obedience=float(base.get("command_obedience", 0.5)),
        command_comprehension=float(base.get("command_comprehension", 0.5)),
        teamwork_skill=float(base.get("teamwork_skill", 0.5)),
        morale=float(base.get("morale", 0.5)),
        panic_action_rate=float(base.get("panic_action_rate", 0.0)),
        hesitation_rate=float(base.get("hesitation_rate", 0.0)),
        misplay_tendency=float(base.get("misplay_tendency", 0.0)),
        communication_method=str(base.get("communication_method", "VOICE")),
        noise_tolerance=float(base.get("noise_tolerance", 0.5)),
        requires_line_of_sight_for_command=bool(
            base.get("requires_line_of_sight_for_command", True)
        ),
        current_order_text=str(current_order_text),
        current_order_priority=str(current_order_priority),
    )


def apply_battle_growth(
    combatant: BattleCombatant,
    *,
    survived: bool = True,
    acted: bool = True,
    followed_order: bool = False,
) -> None:
    """
    戦闘後の軽量成長。
    大きな成長ではなく、将来変化する余地を残す。
    """
    growth = _read_snapshot(combatant, "growth_stats", {})
    if not isinstance(growth, dict):
        growth = {}

    exp = int(growth.get("battle_exp_points", 0) or 0)

    if survived:
        exp += 1
    if acted:
        exp += 1
    if followed_order:
        exp += 1

    growth["battle_exp_points"] = exp
    _write_snapshot(combatant, "growth_stats", growth)

    # 簡易成長: 経験が一定値を超えたら panic を少し減らす
    dynamic_traits = _read_snapshot(combatant, "dynamic_traits", {})
    if not isinstance(dynamic_traits, dict):
        dynamic_traits = {}

    if exp >= 10:
        dynamic_traits["more_stable_under_pressure"] = True

    _write_snapshot(combatant, "dynamic_traits", dynamic_traits)


def apply_post_battle_progression(
    combatant: BattleCombatant,
    *,
    battle_state: str,
    survived: bool = True,
    acted: bool = True,
    followed_order: bool = False,
) -> None:
    apply_battle_growth(
        combatant,
        survived=survived,
        acted=acted,
        followed_order=followed_order,
    )

    growth = _read_snapshot(combatant, "growth_stats", {})
    if not isinstance(growth, dict):
        growth = {}
    growth["battle_count"] = int(growth.get("battle_count", 0) or 0) + 1
    if str(battle_state).upper().strip() == "RESOLVED":
        growth["victory_count"] = int(growth.get("victory_count", 0) or 0) + 1
    _write_snapshot(combatant, "growth_stats", growth)

    controller_type = str(_read_snapshot(combatant, "controller_type", "") or "").upper().strip()
    if combatant.side != "ALLY" or combatant.is_player_controlled or controller_type != "ALLY_AI":
        return

    relationship = _read_snapshot(combatant, "relationship_modifiers", {})
    if not isinstance(relationship, dict):
        relationship = {}

    trust = float(relationship.get("trust_in_leader", 0.0) or 0.0)
    trust_delta = 0.0
    if str(battle_state).upper().strip() == "RESOLVED":
        trust_delta += 0.05
    elif str(battle_state).upper().strip() == "DEFEATED":
        trust_delta -= 0.02

    if followed_order:
        trust_delta += 0.03
    if not survived:
        trust_delta -= 0.04

    relationship["trust_in_leader"] = round(
        _clamp_float(trust + trust_delta, 0.0, 1.0),
        3,
    )
    _write_snapshot(combatant, "relationship_modifiers", relationship)


def upsert_world_combatant_progress(
    db: Session,
    *,
    world_id: int,
    battle_id: int,
    combatant: BattleCombatant,
) -> None:
    entity_id = str(combatant.entity_id or "").strip()
    if not entity_id:
        return

    progress = (
        db.query(WorldCombatantProgress)
        .filter(
            WorldCombatantProgress.world_id == world_id,
            WorldCombatantProgress.entity_id == entity_id,
        )
        .first()
    )
    if not progress:
        progress = WorldCombatantProgress(
            world_id=world_id,
            entity_id=entity_id,
            display_name=combatant.display_name,
        )

    progress.display_name = combatant.display_name
    progress.growth_stats_json = json.dumps(
        _read_snapshot(combatant, "growth_stats", {}),
        ensure_ascii=False,
    )
    progress.relationship_modifiers_json = json.dumps(
        _read_snapshot(combatant, "relationship_modifiers", {}),
        ensure_ascii=False,
    )
    progress.updated_from_battle_id = battle_id
    db.add(progress)


def hydrate_combatant_from_world_progress(
    db: Session,
    *,
    world_id: int,
    combatant: BattleCombatant,
) -> bool:
    entity_id = str(combatant.entity_id or "").strip()
    controller_type = str(_read_snapshot(combatant, "controller_type", "") or "").upper().strip()
    if not entity_id or combatant.side != "ALLY" or combatant.is_player_controlled or controller_type != "ALLY_AI":
        return False

    progress = (
        db.query(WorldCombatantProgress)
        .filter(
            WorldCombatantProgress.world_id == world_id,
            WorldCombatantProgress.entity_id == entity_id,
        )
        .first()
    )
    if not progress:
        return False

    growth = _safe_load_json_dict(progress.growth_stats_json)
    relationship = _safe_load_json_dict(progress.relationship_modifiers_json)
    if growth:
        _write_snapshot(combatant, "growth_stats", growth)
    if relationship:
        _write_snapshot(combatant, "relationship_modifiers", relationship)
    return bool(growth or relationship)


# =========================
# 戦場・通信・命令
# =========================

def extract_battlefield_signal_context(battle: BattleInstance) -> dict[str, Any]:
    """
    現段階では battle_instance だけでは詳細戦場情報を持たないため、
    将来拡張しやすい最小ダミー文脈を返す。
    """
    return {
        "noise_level": "medium",
        "visibility_level": "normal",
        "line_of_sight_ok": True,
    }


def _noise_factor(noise_level: str) -> float:
    mapping = {
        "low": 1.0,
        "medium": 0.75,
        "high": 0.45,
        "extreme": 0.2,
    }
    return mapping.get(noise_level, 0.75)


def can_receive_order(
    profile: CombatAiProfile,
    *,
    battlefield_context: dict[str, Any],
) -> tuple[bool, bool]:
    """
    return:
    - received: 指示が届いたか
    - communication_blocked: 伝達失敗したか
    """
    if not profile.current_order_text:
        return False, False

    if profile.communication_method in {"MAGIC_LINK", "SPIRIT_LINK", "SHARED_MIND"}:
        return True, False

    noise_level = str(battlefield_context.get("noise_level", "medium"))
    line_of_sight_ok = bool(battlefield_context.get("line_of_sight_ok", True))

    receive_score = profile.noise_tolerance * _noise_factor(noise_level)

    if profile.requires_line_of_sight_for_command and not line_of_sight_ok:
        receive_score *= 0.4

    received = random.random() < receive_score
    return received, (not received)


def interpret_order(
    profile: CombatAiProfile,
    *,
    received: bool,
) -> tuple[bool, bool]:
    """
    return:
    - understood
    - obeyed
    """
    if not received or not profile.current_order_text:
        return False, False

    understood = random.random() < profile.command_comprehension
    if not understood:
        return False, False

    obeyed = random.random() < profile.command_obedience
    return True, obeyed


# =========================
# 判断補助
# =========================

def _hp_ratio(combatant: BattleCombatant) -> float:
    if combatant.hp_max <= 0:
        return 0.0
    return combatant.hp_current / combatant.hp_max


def _is_healer(profile: CombatAiProfile) -> bool:
    return profile.combat_role in {"healer", "support"}


def _is_civilian(profile: CombatAiProfile) -> bool:
    return bool(profile.base_traits.get("civilian", False))


def _is_named_style_ai(profile: CombatAiProfile) -> bool:
    if profile.controller_type == "NAMED_AI":
        return True

    # ユニーク味方NPCなど、ALLY_AIでも unique 扱いにしたい場合
    if profile.controller_type == "ALLY_AI":
        if bool(profile.base_traits.get("unique", False)):
            return True
        if bool(profile.dynamic_traits.get("named_mode", False)):
            return True

    return False

def _experience_rank(profile: CombatAiProfile) -> int:
    mapping = {
        "NONE": 0,
        "LOW": 1,
        "TRAINED": 2,
        "VETERAN": 3,
        "ELITE": 4,
    }
    return mapping.get(profile.combat_experience, 1)


def _judgment_rank(profile: CombatAiProfile) -> int:
    mapping = {
        "LOW": 0,
        "MEDIUM": 1,
        "HIGH": 2,
    }
    return mapping.get(profile.tactical_judgment, 0)


def _choose_basic_target(
    db: Session,
    battle_id: int,
    *,
    target_side: str,
) -> BattleCombatant | None:
    return (
        db.query(BattleCombatant)
        .filter(
            BattleCombatant.battle_id == battle_id,
            BattleCombatant.side == target_side,
            BattleCombatant.state == "ACTIVE",
        )
        .order_by(BattleCombatant.hp_current.asc(), BattleCombatant.combatant_id.asc())
        .first()
    )


# =========================
# 味方NPC / MOB / ネームド敵の決定
# =========================

def decide_action_for_combatant(
    db: Session,
    *,
    battle: BattleInstance,
    actor: BattleCombatant,
) -> AiDecision:
    profile = build_ai_profile_for_combatant(actor)
    battlefield_context = extract_battlefield_signal_context(battle)

    received, communication_blocked = can_receive_order(
        profile,
        battlefield_context=battlefield_context,
    )
    order_understood, order_obeyed = interpret_order(profile, received=received)

    panic_modified = False
    misplay_triggered = False

    # 臆病・未熟な民間人はかなり不安定
    if _is_civilian(profile):
        if random.random() < profile.panic_action_rate:
            panic_modified = True
            if _hp_ratio(actor) < 0.8:
                return AiDecision(
                    selected_action_type="WAIT",
                    selected_target_id=None,
                    selected_tactic_text="怯えて動けない",
                    reason_summary="恐慌状態により有効行動を取れなかった。",
                    order_received_text=profile.current_order_text,
                    order_understood=order_understood,
                    order_obeyed=False,
                    panic_modified=True,
                    misplay_triggered=False,
                    communication_blocked=communication_blocked,
                )

    # 誤行動
    if random.random() < profile.misplay_tendency:
        misplay_triggered = True
        if _is_civilian(profile):
            return AiDecision(
                selected_action_type="ATTACK",
                selected_target_id=None,
                selected_tactic_text="恐慌のまま無我夢中で殴りかかる",
                reason_summary="未熟さと恐慌により誤った攻撃行動を選んだ。",
                order_received_text=profile.current_order_text,
                order_understood=order_understood,
                order_obeyed=False,
                panic_modified=panic_modified,
                misplay_triggered=True,
                communication_blocked=communication_blocked,
            )

    # ためらい
    if random.random() < profile.hesitation_rate:
        return AiDecision(
            selected_action_type="WAIT",
            selected_target_id=None,
            selected_tactic_text="様子をうかがう",
            reason_summary="判断を迷い、即断できなかった。",
            order_received_text=profile.current_order_text,
            order_understood=order_understood,
            order_obeyed=False,
            panic_modified=panic_modified,
            misplay_triggered=misplay_triggered,
            communication_blocked=communication_blocked,
        )

    # 命令が通り、かつ従う場合
    if profile.current_order_text and order_obeyed:
        order_text = profile.current_order_text

        if "守" in order_text or "護" in order_text or "防御" in order_text:
            return AiDecision(
                selected_action_type="DEFEND",
                selected_target_id=None,
                selected_tactic_text="指示に従い防御を固める",
                reason_summary="受領した命令を理解し、防御を優先した。",
                order_received_text=order_text,
                order_understood=True,
                order_obeyed=True,
                panic_modified=panic_modified,
                misplay_triggered=misplay_triggered,
                communication_blocked=communication_blocked,
            )

        if "術師" in order_text or "後衛" in order_text or "弱い敵" in order_text:
            target_side = "ENEMY" if actor.side == "ALLY" else "ALLY"
            target = _choose_basic_target(db, battle.battle_id, target_side=target_side)
            return AiDecision(
                selected_action_type="ATTACK",
                selected_target_id=target.combatant_id if target else None,
                selected_tactic_text="指示対象を優先して狙う",
                reason_summary="受領した命令を理解し、指定傾向の目標を狙った。",
                order_received_text=order_text,
                order_understood=True,
                order_obeyed=True,
                panic_modified=panic_modified,
                misplay_triggered=misplay_triggered,
                communication_blocked=communication_blocked,
            )

        if "回復" in order_text and _is_healer(profile):
            return AiDecision(
                selected_action_type="SPELL",
                selected_target_id=None,
                selected_tactic_text="指示に従い回復を優先する",
                reason_summary="受領した命令を理解し、支援行動を優先した。",
                order_received_text=order_text,
                order_understood=True,
                order_obeyed=True,
                panic_modified=panic_modified,
                misplay_triggered=misplay_triggered,
                communication_blocked=communication_blocked,
            )

    # ネームドAIの入口
    if _is_named_style_ai(profile):
        named_decision = decide_named_or_unique_action(
            db,
            battle=battle,
            actor=actor,
            profile=profile,
            order_understood=order_understood,
            order_obeyed=order_obeyed,
            communication_blocked=communication_blocked,
        )

        return AiDecision(
            selected_action_type=str(named_decision["selected_action_type"]),
            selected_target_id=named_decision["selected_target_id"],
            selected_tactic_text=str(named_decision["selected_tactic_text"]),
            reason_summary=str(named_decision["reason_summary"]),
            order_received_text=profile.current_order_text,
            order_understood=order_understood,
            order_obeyed=order_obeyed,
            panic_modified=panic_modified,
            misplay_triggered=misplay_triggered,
            communication_blocked=communication_blocked,
        )

    # ヒーラー系味方AI
    if _is_healer(profile):
        allies = (
            db.query(BattleCombatant)
            .filter(
                BattleCombatant.battle_id == battle.battle_id,
                BattleCombatant.side == actor.side,
                BattleCombatant.state == "ACTIVE",
            )
            .order_by(BattleCombatant.hp_current.asc(), BattleCombatant.combatant_id.asc())
            .all()
        )
        low_ally = None
        for ally in allies:
            if _hp_ratio(ally) <= 0.5:
                low_ally = ally
                break

        available_spell_keys = _read_snapshot(actor, "available_spell_keys", [])
        if low_ally and "minor_heal" in available_spell_keys:
            return AiDecision(
                selected_action_type="SPELL",
                selected_target_id=low_ally.combatant_id,
                selected_tactic_text="危険な味方を癒やす",
                reason_summary="支援役として負傷者の回復を優先した。",
                order_received_text=profile.current_order_text,
                order_understood=order_understood,
                order_obeyed=order_obeyed,
                panic_modified=panic_modified,
                misplay_triggered=misplay_triggered,
                communication_blocked=communication_blocked,
            )
        
    # 民間人 / 未熟AI
    if _is_civilian(profile) or _experience_rank(profile) == 0:
        if _hp_ratio(actor) <= 0.6:
            return AiDecision(
                selected_action_type="DEFEND",
                selected_target_id=None,
                selected_tactic_text="身をすくめて被害を避けようとする",
                reason_summary="未熟さのため、積極行動より身を守る選択をした。",
                order_received_text=profile.current_order_text,
                order_understood=order_understood,
                order_obeyed=order_obeyed,
                panic_modified=panic_modified,
                misplay_triggered=misplay_triggered,
                communication_blocked=communication_blocked,
            )

        target_side = "ENEMY" if actor.side == "ALLY" else "ALLY"
        target = _choose_basic_target(db, battle.battle_id, target_side=target_side)

        return AiDecision(
            selected_action_type="ATTACK",
            selected_target_id=target.combatant_id if target else None,
            selected_tactic_text="目の前の敵へ無我夢中で攻撃する",
            reason_summary="未熟なため、高度な戦術ではなく単純行動を選んだ。",
            order_received_text=profile.current_order_text,
            order_understood=order_understood,
            order_obeyed=order_obeyed,
            panic_modified=panic_modified,
            misplay_triggered=misplay_triggered,
            communication_blocked=communication_blocked,
        )

    # 通常の味方 / MOB
    target_side = "ENEMY" if actor.side == "ALLY" else "ALLY"
    target = _choose_basic_target(db, battle.battle_id, target_side=target_side)

    if _hp_ratio(actor) <= 0.4 and profile.behavior_mode in {"protective", "supportive", "cautious"}:
        return AiDecision(
            selected_action_type="DEFEND",
            selected_target_id=None,
            selected_tactic_text="慎重に構え直して被害を抑える",
            reason_summary="損耗が進んでいるため、防御を優先した。",
            order_received_text=profile.current_order_text,
            order_understood=order_understood,
            order_obeyed=order_obeyed,
            panic_modified=panic_modified,
            misplay_triggered=misplay_triggered,
            communication_blocked=communication_blocked,
        )

    tactic_text = "隙を見て攻め込む"
    if _judgment_rank(profile) >= 1 and _experience_rank(profile) >= 2:
        tactic_text = "相手の体勢の乱れを狙って踏み込む"

    available_spell_keys = _read_snapshot(actor, "available_spell_keys", [])
    target_side = "ENEMY" if actor.side == "ALLY" else "ALLY"
    target = _choose_basic_target(db, battle.battle_id, target_side=target_side)

    if "ember_shot" in available_spell_keys and _judgment_rank(profile) >= 1:
        return AiDecision(
            selected_action_type="SPELL",
            selected_target_id=target.combatant_id if target else None,
            selected_tactic_text="魔力の射線を通し、敵の弱った箇所を焼く",
            reason_summary="判断力と使用可能魔法に基づき、攻撃魔法を選択した。",
            order_received_text=profile.current_order_text,
            order_understood=order_understood,
            order_obeyed=order_obeyed,
            panic_modified=panic_modified,
            misplay_triggered=misplay_triggered,
            communication_blocked=communication_blocked,
        )

    return AiDecision(
        selected_action_type="ATTACK",
        selected_target_id=target.combatant_id if target else None,
        selected_tactic_text=tactic_text,
        reason_summary="役割と経験に基づき、標準的な攻撃判断を行った。",
        order_received_text=profile.current_order_text,
        order_understood=order_understood,
        order_obeyed=order_obeyed,
        panic_modified=panic_modified,
        misplay_triggered=misplay_triggered,
        communication_blocked=communication_blocked,
    )


# =========================
# 指示反映
# =========================

def set_companion_order(
    combatant: BattleCombatant,
    *,
    order_text: str,
    priority: str = "NORMAL",
) -> None:
    _write_snapshot(combatant, "current_order_text", order_text)
    _write_snapshot(combatant, "current_order_priority", priority)


def clear_companion_order(combatant: BattleCombatant) -> None:
    _write_snapshot(combatant, "current_order_text", "")
    _write_snapshot(combatant, "current_order_priority", "NORMAL")


# =========================
# snapshot 初期化補助
# combatant 作成時に使える
# =========================

def initialize_ai_snapshot(
    combatant: BattleCombatant,
    *,
    ai_profile_key: str,
    controller_type: str | None = None,
) -> None:
    profile_dict = get_ai_profile_dict(ai_profile_key)

    _write_snapshot(combatant, "ai_profile_key", ai_profile_key)
    _write_snapshot(
        combatant,
        "controller_type",
        controller_type if controller_type is not None else profile_dict.get("controller_type", "MOB_AI"),
    )
    _write_snapshot(combatant, "dynamic_traits", profile_dict.get("dynamic_traits", {}))
    _write_snapshot(combatant, "growth_stats", profile_dict.get("growth_stats", {}))
    _write_snapshot(
        combatant,
        "relationship_modifiers",
        profile_dict.get("relationship_modifiers", {}),
    )
    _write_snapshot(
        combatant,
        "temporary_state_tags",
        profile_dict.get("temporary_state_tags", []),
    )
    _write_snapshot(
        combatant,
        "current_order_text",
        profile_dict.get("current_order_text", ""),
    )
    _write_snapshot(
        combatant,
        "current_order_priority",
        profile_dict.get("current_order_priority", "NORMAL"),
    )


# =========================
# 表示用補助
# =========================

def build_ai_profile_preview(combatant: BattleCombatant) -> dict[str, Any]:
    profile = build_ai_profile_for_combatant(combatant)
    return {
        "profile_key": profile.profile_key,
        "controller_type": profile.controller_type,
        "combat_role": profile.combat_role,
        "behavior_mode": profile.behavior_mode,
        "base_traits_json": json.dumps(profile.base_traits, ensure_ascii=False),
        "dynamic_traits_json": json.dumps(profile.dynamic_traits, ensure_ascii=False),
        "growth_stats_json": json.dumps(profile.growth_stats, ensure_ascii=False),
        "relationship_modifiers_json": json.dumps(profile.relationship_modifiers, ensure_ascii=False),
        "temporary_state_tags_json": json.dumps(profile.temporary_state_tags, ensure_ascii=False),
        "combat_experience": profile.combat_experience,
        "tactical_judgment": profile.tactical_judgment,
        "command_obedience": profile.command_obedience,
        "command_comprehension": profile.command_comprehension,
        "teamwork_skill": profile.teamwork_skill,
        "morale": profile.morale,
        "panic_action_rate": profile.panic_action_rate,
        "hesitation_rate": profile.hesitation_rate,
        "misplay_tendency": profile.misplay_tendency,
        "communication_method": profile.communication_method,
        "noise_tolerance": profile.noise_tolerance,
        "requires_line_of_sight_for_command": profile.requires_line_of_sight_for_command,
        "current_order_text": profile.current_order_text,
        "current_order_priority": profile.current_order_priority,
    }
