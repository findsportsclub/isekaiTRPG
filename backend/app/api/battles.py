import json

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.world import World
from app.models.battle_instance import BattleInstance
from app.models.battle_combatant import BattleCombatant
from app.models.battle_action_log import BattleActionLog
from app.schemas.battle import (
    CreateBattleRequest,
    BattleCreateResponse,
    BattleCombatantResponse,
    BattleDetailResponse,
    CreateCombatantRequest,
    CombatantCreateResponse,
    BasicAttackRequest,
    BasicAttackResponse,
    BattleActionLogResponse,
    BasicDefendRequest,
    BasicDefendResponse,
    AdvanceTurnRequest,
    AdvanceTurnResponse,
    TurnOrderItem,
    BattleTurnOrderResponse,
    CompanionOrderRequest,
    CompanionOrderResponse,
    CombatAiProfileResponse,
    CombatDecisionPreviewResponse,
    UseSkillRequest,
    UseSkillResponse,
    CombatantUsablesResponse,
    UsableSkillItem,
    UsableSpellItem,
)
from app.services.simple_battle_resolver import (
    resolve_basic_attack,
    resolve_basic_defend,
    _read_snapshot,
    _read_controller_type,
    resolve_registered_skill,
    resolve_registered_spell,
    get_usable_skills_and_spells,
)
from app.services.battle_flow_service import (
    advance_turn_and_run_auto_phases,
    get_turn_order,
)
from app.services.enemy_ai_service import (
    initialize_ai_snapshot,
    set_companion_order,
    build_ai_profile_preview,
    hydrate_combatant_from_world_progress,
)
from app.services.hub_service import get_hub_resource_snapshot
from app.services.battle_registry import build_equipment_bonus_summary

router = APIRouter(prefix="/api", tags=["battles"])


def _safe_load_json_dict(json_text: str) -> dict:
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _resolve_registered_action_definition(action_key: str):
    from app.services.battle_registry import get_skill, get_spell

    skill = get_skill(action_key)
    if skill:
        return skill

    spell = get_spell(action_key)
    if spell:
        return spell

    return None


def _normalize_use_skill_target(
    db: Session,
    *,
    battle_id: int,
    actor: BattleCombatant,
    requested_target_id: int | None,
    target_type: str,
) -> int:
    normalized_target_type = str(target_type).strip().lower()

    if normalized_target_type == "self":
        return actor.combatant_id

    if requested_target_id is None:
        raise HTTPException(status_code=400, detail="target_combatant_id is required")

    target = (
        db.query(BattleCombatant)
        .filter(BattleCombatant.combatant_id == requested_target_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=400, detail="Target not found")
    if target.battle_id != battle_id:
        raise HTTPException(status_code=400, detail="Target does not belong to the specified battle")
    if target.state != "ACTIVE":
        raise HTTPException(status_code=400, detail="Target is not active")

    if normalized_target_type == "single_enemy" and target.side == actor.side:
        raise HTTPException(status_code=400, detail="single_enemy target must be on the opposing side")

    if normalized_target_type == "single_ally" and target.side != actor.side:
        raise HTTPException(status_code=400, detail="single_ally target must be on the same side")

    if normalized_target_type not in {"single_enemy", "single_ally"}:
        raise HTTPException(status_code=400, detail=f"Unsupported target_type: {target_type}")

    return target.combatant_id


@router.post("/battles", response_model=BattleCreateResponse)
def create_battle(request: CreateBattleRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == request.world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        battle = BattleInstance(
            world_id=request.world_id,
            location_id=request.location_id,
            battlefield_id=request.battlefield_id,
            battle_type=request.battle_type,
            source_type=request.source_type,
            source_ref_id=request.source_ref_id,
            state="ACTIVE",
            turn_no=1,
            objective_type=request.objective_type,
            objective_snapshot_json="{}",
            victory_condition_json='{"type":"defeat_all_enemies"}',
            defeat_condition_json='{"type":"player_down"}',
            battle_difficulty_snapshot_json="{}",
        )
        hub_resources = get_hub_resource_snapshot(db, world_id=request.world_id)
        purchased_equipment = list(hub_resources.get("purchased_equipment", []) or [])
        if hub_resources.get("crafted_supplies") or int(hub_resources.get("material_credit", 0) or 0) > 0 or purchased_equipment:
            battle.battle_difficulty_snapshot_json = json.dumps(
                {
                    "hub_support": {
                        "crafted_supplies": dict(hub_resources.get("crafted_supplies", {}) or {}),
                        "material_credit": int(hub_resources.get("material_credit", 0) or 0),
                        "purchased_equipment": purchased_equipment,
                        "equipment_bonus_summary": build_equipment_bonus_summary([str(x) for x in purchased_equipment]),
                    }
                },
                ensure_ascii=False,
            )
        db.add(battle)
        db.commit()
        db.refresh(battle)

        return BattleCreateResponse(
            battle_id=battle.battle_id,
            state=battle.state,
            turn_no=battle.turn_no,
        )
    finally:
        db.close()


@router.get("/battles/{battle_id}", response_model=BattleDetailResponse)
def get_battle_detail(battle_id: int):
    db: Session = SessionLocal()
    try:
        battle = db.query(BattleInstance).filter(BattleInstance.battle_id == battle_id).first()
        if not battle:
            raise HTTPException(status_code=404, detail="Battle not found")

        combatants = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.battle_id == battle_id)
            .order_by(BattleCombatant.join_order.asc(), BattleCombatant.combatant_id.asc())
            .all()
        )

        return BattleDetailResponse(
            battle_id=battle.battle_id,
            world_id=battle.world_id,
            location_id=battle.location_id,
            battlefield_id=battle.battlefield_id,
            battle_type=battle.battle_type,
            source_type=battle.source_type,
            state=battle.state,
            turn_no=battle.turn_no,
            objective_type=battle.objective_type,
            combatants=[
                BattleCombatantResponse(
                    combatant_id=c.combatant_id,
                    display_name=c.display_name,
                    side=c.side,
                    role=c.role,
                    hp_current=c.hp_current,
                    hp_max=c.hp_max,
                    mp_current=c.mp_current,
                    mp_max=c.mp_max,
                    state=c.state,
                    defend_active=bool(_read_snapshot(c, "defend_active", False)),
                    defend_used_tags_json=json.dumps(
                        _read_snapshot(c, "defend_used_tags", []),
                        ensure_ascii=False,
                    ),
                    has_acted_this_turn=bool(_read_snapshot(c, "acted_this_turn", False)),
                    range_band=str(_read_snapshot(c, "range_band", "MID")),
                    position_tags_json=json.dumps(
                        _read_snapshot(c, "position_tags", []),
                        ensure_ascii=False,
                    ),
                    controller_type=_read_controller_type(c),
                    ai_profile_key=str(_read_snapshot(c, "ai_profile_key", "")),
                    current_order_text=str(_read_snapshot(c, "current_order_text", "")),
                    available_skill_keys_json=json.dumps(
                        _read_snapshot(c, "available_skill_keys", []),
                        ensure_ascii=False,
                    ),
                    available_spell_keys_json=json.dumps(
                        _read_snapshot(c, "available_spell_keys", []),
                        ensure_ascii=False,
                    ),
                    equipped_item_keys_json=json.dumps(
                        _read_snapshot(c, "equipped_item_keys", []),
                        ensure_ascii=False,
                    ),
                )
                for c in combatants
            ],
        )
    finally:
        db.close()


@router.post("/battle-combatants", response_model=CombatantCreateResponse)
def create_battle_combatant(request: CreateCombatantRequest):
    db: Session = SessionLocal()
    try:
        battle = db.query(BattleInstance).filter(BattleInstance.battle_id == request.battle_id).first()
        if not battle:
            raise HTTPException(status_code=404, detail="Battle not found")

        join_order = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.battle_id == request.battle_id)
            .count()
            + 1
        )

        combatant = BattleCombatant(
            battle_id=request.battle_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            display_name=request.display_name,
            side=request.side,
            role=request.role,
            join_order=join_order,
            hp_current=request.hp_current,
            hp_max=request.hp_max,
            mp_current=request.mp_current,
            mp_max=request.mp_max,
            atk=request.atk,
            defense=request.defense,
            mag=request.mag,
            res=request.res,
            spd=request.spd,
            hit=request.hit,
            eva=request.eva,
            crit=request.crit,
            guard_rate=request.guard_rate,
            state="ACTIVE",
            initiative_score=request.spd,
            is_player_controlled=request.is_player_controlled,
            snapshot_json="{}",
        )

        db.add(combatant)
        db.commit()
        db.refresh(combatant)

        ai_profile_key = request.ai_profile_key.strip() if request.ai_profile_key else ""
        if not ai_profile_key:
            if request.is_player_controlled:
                ai_profile_key = "player_manual"
            elif request.side == "ALLY":
                ai_profile_key = "ally_guard_novice"
            else:
                ai_profile_key = "mob_basic_melee"

        controller_type = "PLAYER" if request.is_player_controlled else ("ALLY_AI" if request.side == "ALLY" else "MOB_AI")
        initialize_ai_snapshot(
            combatant,
            ai_profile_key=ai_profile_key,
            controller_type=controller_type,
        )
        hydrate_combatant_from_world_progress(
            db,
            world_id=battle.world_id,
            combatant=combatant,
        )

        if request.loadout_key:
            from app.services.simple_battle_resolver import _write_snapshot
            from app.services.battle_registry import (
                get_loadout_skill_keys,
                get_loadout_spell_keys,
                get_loadout_equipment_keys,
            )

            _write_snapshot(combatant, "loadout_key", request.loadout_key)
            _write_snapshot(combatant, "available_skill_keys", get_loadout_skill_keys(request.loadout_key))
            _write_snapshot(combatant, "available_spell_keys", get_loadout_spell_keys(request.loadout_key))
            _write_snapshot(combatant, "equipped_item_keys", get_loadout_equipment_keys(request.loadout_key))
        else:
            from app.services.simple_battle_resolver import _write_snapshot
            _write_snapshot(combatant, "loadout_key", "")
            _write_snapshot(combatant, "available_skill_keys", [])
            _write_snapshot(combatant, "available_spell_keys", [])
            _write_snapshot(combatant, "equipped_item_keys", [])

        _write_snapshot(combatant, "range_band", "MID")
        _write_snapshot(combatant, "position_tags", [])

        db.add(combatant)
        db.commit()
        db.refresh(combatant)

        return CombatantCreateResponse(
            combatant_id=combatant.combatant_id,
            display_name=combatant.display_name,
            side=combatant.side,
            state=combatant.state,
        )
    finally:
        db.close()


@router.post("/battles/basic-attack", response_model=BasicAttackResponse)
def execute_basic_attack(request: BasicAttackRequest):
    db: Session = SessionLocal()
    try:
        declaration = resolve_basic_attack(
            db,
            battle_id=request.battle_id,
            turn_no=request.turn_no,
            actor_combatant_id=request.actor_combatant_id,
            target_combatant_id=request.target_combatant_id,
            declared_tactic_text=request.declared_tactic_text,
            risk_level=request.risk_level,
        )

        return BasicAttackResponse(
            declaration_id=declaration.declaration_id,
            resolution_status=declaration.resolution_status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/battles/basic-defend", response_model=BasicDefendResponse)
def execute_basic_defend(request: BasicDefendRequest):
    db: Session = SessionLocal()
    try:
        declaration = resolve_basic_defend(
            db,
            battle_id=request.battle_id,
            turn_no=request.turn_no,
            actor_combatant_id=request.actor_combatant_id,
            declared_tactic_text=request.declared_tactic_text,
            risk_level=request.risk_level,
        )

        return BasicDefendResponse(
            declaration_id=declaration.declaration_id,
            resolution_status=declaration.resolution_status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.post("/battles/use-skill", response_model=UseSkillResponse)
def use_skill_or_spell(request: UseSkillRequest):
    db: Session = SessionLocal()
    try:
        actor = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == request.actor_combatant_id)
            .first()
        )
        if not actor:
            raise HTTPException(status_code=404, detail="Actor not found")
        if actor.battle_id != request.battle_id:
            raise HTTPException(status_code=400, detail="Actor does not belong to the specified battle")

        declaration = None
        definition = _resolve_registered_action_definition(request.skill_key)
        if not definition:
            raise HTTPException(status_code=404, detail="Skill/Spell not found")

        resolved_target_id = _normalize_use_skill_target(
            db,
            battle_id=request.battle_id,
            actor=actor,
            requested_target_id=request.target_combatant_id,
            target_type=definition.target_type,
        )

        if hasattr(definition, "skill_key"):
            declaration = resolve_registered_skill(
                db,
                battle_id=request.battle_id,
                turn_no=request.turn_no,
                actor_combatant_id=request.actor_combatant_id,
                target_combatant_id=resolved_target_id,
                skill_key=request.skill_key,
                declared_tactic_text=request.declared_tactic_text,
                risk_level=request.risk_level,
            )
        else:
            declaration = resolve_registered_spell(
                db,
                battle_id=request.battle_id,
                turn_no=request.turn_no,
                actor_combatant_id=request.actor_combatant_id,
                target_combatant_id=resolved_target_id,
                spell_key=request.skill_key,
                declared_tactic_text=request.declared_tactic_text,
                risk_level=request.risk_level,
            )

        return UseSkillResponse(
            declaration_id=declaration.declaration_id,
            resolution_status=declaration.resolution_status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.post("/battles/advance-turn", response_model=AdvanceTurnResponse)
def advance_battle_turn(request: AdvanceTurnRequest):
    db: Session = SessionLocal()
    try:
        result = advance_turn_and_run_auto_phases(db, request.battle_id)
        return AdvanceTurnResponse(
            battle_id=result["battle_id"],
            turn_no=result["turn_no"],
            state=result["state"],
            acted_enemy_count=result["acted_enemy_count"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.get("/battles/{battle_id}/turn-order", response_model=BattleTurnOrderResponse)
def get_battle_turn_order(battle_id: int):
    db: Session = SessionLocal()
    try:
        result = get_turn_order(db, battle_id)
        return BattleTurnOrderResponse(
            battle_id=result["battle_id"],
            turn_no=result["turn_no"],
            order=[
                TurnOrderItem(
                    combatant_id=item["combatant_id"],
                    display_name=item["display_name"],
                    side=item["side"],
                    spd=item["spd"],
                    state=item["state"],
                    has_acted=item["has_acted"],
                )
                for item in result["order"]
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.post("/battles/companion-order", response_model=CompanionOrderResponse)
def issue_companion_order(request: CompanionOrderRequest):
    db: Session = SessionLocal()
    try:
        combatant = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == request.target_combatant_id)
            .first()
        )
        if not combatant:
            raise HTTPException(status_code=404, detail="Combatant not found")
        if combatant.battle_id != request.battle_id:
            raise HTTPException(status_code=400, detail="Combatant does not belong to the specified battle")

        controller_type = _read_controller_type(combatant)
        if controller_type == "PLAYER":
            raise HTTPException(status_code=400, detail="Cannot issue companion order to player-controlled unit")

        set_companion_order(
            combatant,
            order_text=request.order_text,
            priority=request.priority,
        )
        db.add(combatant)
        db.commit()
        db.refresh(combatant)

        return CompanionOrderResponse(
            battle_id=request.battle_id,
            target_combatant_id=request.target_combatant_id,
            order_text=request.order_text,
            priority=request.priority,
            accepted=True,
        )
    finally:
        db.close()


@router.get("/battles/{battle_id}/combatants/{combatant_id}/ai-profile", response_model=CombatAiProfileResponse)
def get_combatant_ai_profile(battle_id: int, combatant_id: int):
    db: Session = SessionLocal()
    try:
        combatant = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == combatant_id)
            .first()
        )
        if not combatant:
            raise HTTPException(status_code=404, detail="Combatant not found")
        if combatant.battle_id != battle_id:
            raise HTTPException(status_code=400, detail="Combatant does not belong to the specified battle")

        profile = build_ai_profile_preview(combatant)

        return CombatAiProfileResponse(
            profile_key=profile["profile_key"],
            controller_type=profile["controller_type"],
            combat_role=profile["combat_role"],
            behavior_mode=profile["behavior_mode"],
            base_traits_json=profile["base_traits_json"],
            dynamic_traits_json=profile["dynamic_traits_json"],
            growth_stats_json=profile["growth_stats_json"],
            relationship_modifiers_json=profile["relationship_modifiers_json"],
            temporary_state_tags_json=profile["temporary_state_tags_json"],
            combat_experience=profile["combat_experience"],
            tactical_judgment=profile["tactical_judgment"],
            command_obedience=profile["command_obedience"],
            command_comprehension=profile["command_comprehension"],
            teamwork_skill=profile["teamwork_skill"],
            morale=profile["morale"],
            panic_action_rate=profile["panic_action_rate"],
            hesitation_rate=profile["hesitation_rate"],
            misplay_tendency=profile["misplay_tendency"],
            communication_method=profile["communication_method"],
            noise_tolerance=profile["noise_tolerance"],
            requires_line_of_sight_for_command=profile["requires_line_of_sight_for_command"],
            current_order_text=profile["current_order_text"],
            current_order_priority=profile["current_order_priority"],
        )
    finally:
        db.close()

@router.get("/battles/{battle_id}/combatants/{combatant_id}/usables", response_model=CombatantUsablesResponse)
def get_combatant_usables(battle_id: int, combatant_id: int):
    db: Session = SessionLocal()
    try:
        combatant = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == combatant_id)
            .first()
        )
        if not combatant:
            raise HTTPException(status_code=404, detail="Combatant not found")
        if combatant.battle_id != battle_id:
            raise HTTPException(status_code=400, detail="Combatant does not belong to the specified battle")

        data = get_usable_skills_and_spells(combatant)

        return CombatantUsablesResponse(
            battle_id=battle_id,
            combatant_id=combatant_id,
            skill_items=[
                UsableSkillItem(**item) for item in data["skill_items"]
            ],
            spell_items=[
                UsableSpellItem(**item) for item in data["spell_items"]
            ],
        )
    finally:
        db.close()

@router.get(
    "/battles/{battle_id}/combatants/{combatant_id}/ai-decision-preview",
    response_model=CombatDecisionPreviewResponse,
)
def preview_combatant_ai_decision(battle_id: int, combatant_id: int):
    db: Session = SessionLocal()
    try:
        battle = (
            db.query(BattleInstance)
            .filter(BattleInstance.battle_id == battle_id)
            .first()
        )
        if not battle:
            raise HTTPException(status_code=404, detail="Battle not found")

        combatant = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == combatant_id)
            .first()
        )
        if not combatant:
            raise HTTPException(status_code=404, detail="Combatant not found")
        if combatant.battle_id != battle_id:
            raise HTTPException(status_code=400, detail="Combatant does not belong to the specified battle")

        from app.services.enemy_ai_service import decide_action_for_combatant

        decision = decide_action_for_combatant(
            db,
            battle=battle,
            actor=combatant,
        )

        return CombatDecisionPreviewResponse(
            combatant_id=combatant.combatant_id,
            display_name=combatant.display_name,
            controller_type=_read_controller_type(combatant),
            selected_action_type=decision.selected_action_type,
            selected_target_id=decision.selected_target_id,
            selected_tactic_text=decision.selected_tactic_text,
            reason_summary=decision.reason_summary,
            order_received_text=decision.order_received_text,
            order_understood=decision.order_understood,
            order_obeyed=decision.order_obeyed,
            panic_modified=decision.panic_modified,
            misplay_triggered=decision.misplay_triggered,
            communication_blocked=decision.communication_blocked,
        )
    finally:
        db.close()

@router.get("/battles/{battle_id}/logs", response_model=list[BattleActionLogResponse])
def get_battle_logs(battle_id: int):
    db: Session = SessionLocal()
    try:
        battle = db.query(BattleInstance).filter(BattleInstance.battle_id == battle_id).first()
        if not battle:
            raise HTTPException(status_code=404, detail="Battle not found")

        logs = (
            db.query(BattleActionLog)
            .filter(BattleActionLog.battle_id == battle_id)
            .order_by(BattleActionLog.turn_no.asc(), BattleActionLog.action_log_id.asc())
            .all()
        )

        combatants = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.battle_id == battle_id)
            .all()
        )
        combatant_name_map = {c.combatant_id: c.display_name for c in combatants}

        return [
            BattleActionLogResponse(
                action_log_id=log.action_log_id,
                turn_no=log.turn_no,
                declaration_id=log.declaration_id,
                actor_combatant_id=log.actor_combatant_id,
                actor_name=combatant_name_map.get(log.actor_combatant_id, f"#{log.actor_combatant_id}"),
                target_combatant_id=log.target_combatant_id,
                target_name=(
                    combatant_name_map.get(log.target_combatant_id)
                    if log.target_combatant_id is not None
                    else None
                ),
                result_type=log.result_type,
                hit_success=log.hit_success,
                crit_success=log.crit_success,
                guard_success=log.guard_success,
                evade_success=log.evade_success,
                damage_value=log.damage_value,
                hp_after=log.hp_after,
                declared_tactic_text=log.declared_tactic_text,
                used_tags_json=log.used_tags_json,
                narrative_result=log.narrative_result,
                ai_reason_summary="",
                order_applied_text="",
            )
            for log in logs
        ]
    finally:
        db.close()
