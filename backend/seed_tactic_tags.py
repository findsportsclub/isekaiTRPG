import json

from app.db.session import SessionLocal, Base, engine
from app.models.tactic_tag_master import TacticTagMaster


TACTIC_TAGS = [
    {
        "tag_key": "backlight",
        "display_name": "逆光利用",
        "category": "VISIBILITY",
        "description": "太陽や強い光源を背にして相手の視認を乱す戦術。",
        "risk_level": "LOW",
        "allowed_action_types": ["ATTACK", "SKILL"],
        "condition": {
            "requires_light_source": True,
            "requires_outdoor_or_bright_field": True,
        },
        "effect": {
            "enemy_eva_penalty": 6,
            "crit_bonus": 4,
        },
        "stack_rule": "NO_STACK",
        "enabled_flag": True,
        "sort_order": 10,
    },
    {
        "tag_key": "high_ground",
        "display_name": "高所優位",
        "category": "TERRAIN",
        "description": "段差や高所を利用して攻撃角度と視界で優位を取る戦術。",
        "risk_level": "LOW",
        "allowed_action_types": ["ATTACK", "SKILL", "SPELL"],
        "condition": {
            "requires_elevation_advantage": True,
        },
        "effect": {
            "hit_bonus": 8,
            "enemy_melee_hit_penalty": 5,
        },
        "stack_rule": "NO_STACK",
        "enabled_flag": True,
        "sort_order": 20,
    },
    {
        "tag_key": "feint_attack",
        "display_name": "フェイント攻撃",
        "category": "FEINT",
        "description": "虚を突く動きで相手の防御や反応をずらしてから本命を通す戦術。",
        "risk_level": "MEDIUM",
        "allowed_action_types": ["ATTACK", "SKILL"],
        "condition": {
            "requires_direct_engagement": True,
        },
        "effect": {
            "hit_bonus": -4,
            "crit_bonus": 10,
        },
        "stack_rule": "NO_STACK",
        "enabled_flag": True,
        "sort_order": 30,
    },
    {
        "tag_key": "mud_defense",
        "display_name": "ぬかるみ防御",
        "category": "DEFENSE",
        "description": "ぬかるみや重い足場で低く構え、衝撃を受け流す防御姿勢。",
        "risk_level": "LOW",
        "allowed_action_types": ["DEFEND"],
        "condition": {
            "requires_muddy_or_soft_ground": True,
        },
        "effect": {
            "damage_taken_multiplier": 0.9,
            "eva_penalty": 5,
        },
        "stack_rule": "NO_STACK",
        "enabled_flag": True,
        "sort_order": 40,
    },
    {
        "tag_key": "cover_use",
        "display_name": "遮蔽利用",
        "category": "TERRAIN",
        "description": "壁、柱、瓦礫、物陰などを利用して敵の攻撃線を切る戦術。",
        "risk_level": "LOW",
        "allowed_action_types": ["DEFEND", "ATTACK", "SPELL"],
        "condition": {
            "requires_cover": True,
        },
        "effect": {
            "ranged_enemy_hit_penalty": 10,
        },
        "stack_rule": "NO_STACK",
        "enabled_flag": True,
        "sort_order": 50,
    },
]


def upsert_tactic_tags() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for tag in TACTIC_TAGS:
            existing = (
                db.query(TacticTagMaster)
                .filter(TacticTagMaster.tag_key == tag["tag_key"])
                .first()
            )

            if existing:
                existing.display_name = tag["display_name"]
                existing.category = tag["category"]
                existing.description = tag["description"]
                existing.risk_level = tag["risk_level"]
                existing.allowed_action_types_json = json.dumps(
                    tag["allowed_action_types"], ensure_ascii=False
                )
                existing.condition_json = json.dumps(tag["condition"], ensure_ascii=False)
                existing.effect_json = json.dumps(tag["effect"], ensure_ascii=False)
                existing.stack_rule = tag["stack_rule"]
                existing.enabled_flag = tag["enabled_flag"]
                existing.sort_order = tag["sort_order"]
            else:
                db.add(
                    TacticTagMaster(
                        tag_key=tag["tag_key"],
                        display_name=tag["display_name"],
                        category=tag["category"],
                        description=tag["description"],
                        risk_level=tag["risk_level"],
                        allowed_action_types_json=json.dumps(
                            tag["allowed_action_types"], ensure_ascii=False
                        ),
                        condition_json=json.dumps(tag["condition"], ensure_ascii=False),
                        effect_json=json.dumps(tag["effect"], ensure_ascii=False),
                        stack_rule=tag["stack_rule"],
                        enabled_flag=tag["enabled_flag"],
                        sort_order=tag["sort_order"],
                    )
                )

        db.commit()
        print("TACTIC TAGS SEEDED: 5")
    finally:
        db.close()


if __name__ == "__main__":
    upsert_tactic_tags()