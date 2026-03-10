import json

from app.db.session import Base, SessionLocal, engine
from app.models.battle_action_log import BattleActionLog
from app.models.battle_combatant import BattleCombatant
from app.models.battle_instance import BattleInstance
from app.models.battlefield import Battlefield
from app.services.simple_battle_resolver import resolve_basic_attack


def ensure_tables():
    Base.metadata.create_all(bind=engine)


def seed_minimum_battle_data():
    db = SessionLocal()
    try:
        battlefield = Battlefield(
            world_id=1,
            location_id="test_field",
            name="テスト平原",
            overview="簡易戦闘テスト用の開けた場所。",
            terrain_json=json.dumps(
                {
                    "elevation": "low",
                    "narrow_wide": "wide",
                    "cover": "low",
                    "footing": "stable",
                    "entry_routes": ["front"],
                    "escape_routes": ["rear"],
                },
                ensure_ascii=False,
            ),
            environment_json=json.dumps(
                {
                    "time_of_day": "day",
                    "weather": "clear",
                    "brightness": "bright",
                    "visibility": "good",
                    "sound": "open_field",
                    "air": "dry",
                },
                ensure_ascii=False,
            ),
            movement_rules_json=json.dumps(
                {
                    "run": "easy",
                    "slippery": False,
                    "climb_required": False,
                    "mounted_movement": "good",
                    "flying_effect": "stable",
                },
                ensure_ascii=False,
            ),
            tactical_bias_json=json.dumps(
                {
                    "ranged": "medium",
                    "melee": "medium",
                    "ambush": "low",
                    "defense": "low",
                    "encirclement": "medium",
                    "retreat": "good",
                },
                ensure_ascii=False,
            ),
            objective_type="DEFEAT",
            objective_detail_json=json.dumps({}, ensure_ascii=False),
            psychological_effect="視界が開けており、小細工より正面戦闘になりやすい。",
            symbolism_json=json.dumps({"themes": ["trial"]}, ensure_ascii=False),
            meaning_for_protagonist="力試しの場",
            meaning_for_enemy="単なる迎撃地点",
            gm_notes="最小戦闘確認用",
            time_progression_json=json.dumps({}, ensure_ascii=False),
        )
        db.add(battlefield)
        db.commit()
        db.refresh(battlefield)

        battle = BattleInstance(
            world_id=1,
            location_id="test_field",
            battlefield_id=battlefield.battlefield_id,
            battle_type="ENCOUNTER",
            source_type="MANUAL",
            source_ref_id="test_battle_001",
            state="ACTIVE",
            turn_no=1,
            objective_type="DEFEAT",
            objective_snapshot_json=json.dumps(
                {"type": "defeat_all_enemies"},
                ensure_ascii=False,
            ),
            victory_condition_json=json.dumps(
                {"type": "defeat_all_enemies"},
                ensure_ascii=False,
            ),
            defeat_condition_json=json.dumps(
                {"type": "player_down"},
                ensure_ascii=False,
            ),
            battle_difficulty_snapshot_json=json.dumps({}, ensure_ascii=False),
        )
        db.add(battle)
        db.commit()
        db.refresh(battle)

        actor = BattleCombatant(
            battle_id=battle.battle_id,
            entity_type="PLAYER",
            entity_id="player_001",
            display_name="アオ",
            side="ALLY",
            role="FRONT",
            join_order=1,
            hp_current=30,
            hp_max=30,
            mp_current=10,
            mp_max=10,
            atk=12,
            defense=5,
            mag=4,
            res=3,
            spd=8,
            hit=5,
            eva=2,
            crit=5,
            guard_rate=0,
            state="ACTIVE",
            initiative_score=8,
            is_player_controlled=True,
            snapshot_json=json.dumps({}, ensure_ascii=False),
        )
        db.add(actor)

        target = BattleCombatant(
            battle_id=battle.battle_id,
            entity_type="MONSTER",
            entity_id="monster_001",
            display_name="坑道の獣",
            side="ENEMY",
            role="FRONT",
            join_order=2,
            hp_current=24,
            hp_max=24,
            mp_current=0,
            mp_max=0,
            atk=9,
            defense=4,
            mag=0,
            res=2,
            spd=6,
            hit=2,
            eva=1,
            crit=0,
            guard_rate=0,
            state="ACTIVE",
            initiative_score=6,
            is_player_controlled=False,
            snapshot_json=json.dumps({}, ensure_ascii=False),
        )
        db.add(target)

        db.commit()
        db.refresh(actor)
        db.refresh(target)

        return battle.battle_id, actor.combatant_id, target.combatant_id
    finally:
        db.close()


def run_test_attack(battle_id: int, actor_id: int, target_id: int):
    db = SessionLocal()
    try:
        resolve_basic_attack(
            db,
            battle_id=battle_id,
            turn_no=1,
            actor_combatant_id=actor_id,
            target_combatant_id=target_id,
            declared_tactic_text="太陽を背に回り込みながら斬りかかる",
            risk_level="LOW",
        )

        logs = (
            db.query(BattleActionLog)
            .filter(BattleActionLog.battle_id == battle_id)
            .order_by(BattleActionLog.action_log_id.asc())
            .all()
        )

        target = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == target_id)
            .first()
        )

        print("=== BATTLE LOGS ===")
        for log in logs:
            print(
                f"[turn {log.turn_no}] result={log.result_type} "
                f"damage={log.damage_value} hp_after={log.hp_after}"
            )
            print(" tactic:", log.declared_tactic_text)
            print(" tags:", log.used_tags_json)
            print(" text:", log.narrative_result)
            print("---")

        print("=== TARGET STATUS ===")
        print(target.display_name, target.hp_current, target.state)
    finally:
        db.close()


if __name__ == "__main__":
    ensure_tables()
    battle_id, actor_id, target_id = seed_minimum_battle_data()
    run_test_attack(battle_id, actor_id, target_id)