from app.db.session import SessionLocal
from app.services.battle_declaration_service import create_battle_action_declaration


def main():
    db = SessionLocal()
    try:
        declaration = create_battle_action_declaration(
            db,
            battle_id=1,
            turn_no=1,
            actor_combatant_id=1,
            action_type="ATTACK",
            primary_target_combatant_id=2,
            declared_tactic_text="太陽を背に回り込みながら斬りかかる",
            risk_level="LOW",
        )
        print("DECLARATION CREATED:", declaration.declaration_id, declaration.parsed_tags_json)
    finally:
        db.close()


if __name__ == "__main__":
    main()