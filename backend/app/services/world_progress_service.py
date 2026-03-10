from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.quest import Quest
from app.models.world_state import WorldState

SECURITY_QUEST_ID = "security_001"


def clamp_security_score(score: int) -> int:
    return max(0, min(100, int(score)))


def get_security_band(score: int) -> str:
    normalized = clamp_security_score(score)
    if normalized >= 70:
        return "stable"
    if normalized >= 50:
        return "watch"
    if normalized >= 30:
        return "unstable"
    return "lawless"


def build_security_rumors(state: WorldState) -> list[str]:
    band = get_security_band(state.security_score)
    if band == "stable":
        return [
            "衛兵の巡回は機能しており、露骨な無法者の動きはまだ抑えられている。",
            "とはいえ戦局が長引けば、街道の見張りは薄くなりかねない。",
        ]
    if band == "watch":
        return [
            "街道沿いで荷を狙う不審者が出るようになり、村人の帰り足が早くなっている。",
            "衛兵は足りているが、政治の混乱が続けば追い剥ぎが増えると囁かれている。",
        ]
    if band == "unstable":
        return [
            "街道では盗賊崩れの集団が荷馬車を狙い始め、護衛依頼が急増している。",
            "王国側の統制が緩み、村外れでは夜の強盗を恐れて戸締まりが厳しくなった。",
        ]
    return [
        "無法者が堂々と人を襲うようになり、討伐の手が足りない。",
        "戦争と政争の余波で治安は崩れ、盗賊討伐が急務になっている。",
    ]


def sync_security_side_quest(
    db: Session,
    *,
    world_id: int,
    state: WorldState,
) -> Quest | None:
    quest = get_side_quest(db, world_id, SECURITY_QUEST_ID)
    band = get_security_band(state.security_score)

    if state.security_score <= 45:
        if not quest:
            quest = Quest(
                world_id=world_id,
                quest_id=SECURITY_QUEST_ID,
                category="side",
                title="街道の盗賊を討つ",
                status="ACTIVE",
                description="戦争と政争の余波で増えた盗賊や追い剥ぎを押さえ、街道の治安を立て直す。",
                progress=0,
            )
            db.add(quest)
            db.add(
                Log(
                    world_id=world_id,
                    log_type="quest",
                    title="新たな依頼: 街道の盗賊を討つ",
                    body="治安悪化により、街道や村外れで盗賊討伐の依頼が増え始めた。",
                )
            )
        elif quest.status != "CLEARED":
            quest.status = "ACTIVE"

        if quest and quest.status != "CLEARED":
            if band == "lawless":
                quest.description = "盗賊や強盗が公然と出没している。村外れと街道の制圧を急ぎたい。"
            else:
                quest.description = "戦争と政争の余波で増えた盗賊や追い剥ぎを押さえ、街道の治安を立て直す。"
            db.add(quest)
        return quest

    if quest and quest.status != "CLEARED" and state.security_score >= 60 and quest.progress >= 2:
        quest.status = "CLEARED"
        db.add(quest)
        db.add(
            Log(
                world_id=world_id,
                log_type="quest",
                title="クエスト達成: 街道の盗賊を討つ",
                body="村周辺の見回りと討伐が実を結び、街道の治安はひとまず持ち直した。",
            )
        )
    return quest


def get_or_create_world_state(db: Session, world_id: int) -> WorldState:
    state = db.query(WorldState).filter(WorldState.world_id == world_id).first()
    if state:
        if getattr(state, "security_score", None) is None:
            state.security_score = 72
            db.add(state)
            db.flush()
        return state

    state = WorldState(
        world_id=world_id,
        dungeon_score=50,
        faction_score=20,
        demon_score=10,
        security_score=72,
        gold=120,
        tax_debt=12,
        meal_stock=2,
        main_event_title="北坑道の異変",
        main_event_state="ACTIVE",
        quest_progress=0,
        housing_tier="lodging",
    )
    db.add(state)
    db.flush()
    return state


def get_main_quest(db: Session, world_id: int) -> Quest | None:
    return (
        db.query(Quest)
        .filter(Quest.world_id == world_id, Quest.category == "main")
        .order_by(Quest.quest_row_id.asc())
        .first()
    )


def get_side_quest(db: Session, world_id: int, quest_id: str) -> Quest | None:
    return (
        db.query(Quest)
        .filter(Quest.world_id == world_id, Quest.quest_id == quest_id)
        .order_by(Quest.quest_row_id.asc())
        .first()
    )


def apply_world_quest_completion_rules(
    db: Session,
    *,
    world_id: int,
    state: WorldState,
    main_quest: Quest | None = None,
    side_quest_001: Quest | None = None,
) -> None:
    if state.quest_progress < 5:
        sync_security_side_quest(db, world_id=world_id, state=state)
        return

    state.main_event_title = "北坑道の異変を突き止めた"
    state.main_event_state = "CLEARED"

    if main_quest:
        main_quest.title = "北坑道の異変を突き止めた"
        main_quest.status = "CLEARED"
        db.add(main_quest)

    if side_quest_001 and side_quest_001.status == "CLEARED" and side_quest_001.progress >= 2:
        clear_log_exists = (
            db.query(Log)
            .filter(
                Log.world_id == world_id,
                Log.title == "クエスト達成: 坑道の横穴を調べる",
            )
            .first()
        )
        if not clear_log_exists:
            db.add(
                Log(
                    world_id=world_id,
                    log_type="quest",
                    title="クエスト達成: 坑道の横穴を調べる",
                    body="坑道入口の調査により、横穴へ続く隠し裂け目の存在を突き止めた。",
                )
            )

    db.add(state)
    sync_security_side_quest(db, world_id=world_id, state=state)


def apply_battle_resolution_world_progress(
    db: Session,
    *,
    world_id: int,
    battle_id: int,
    battle_state: str,
) -> dict[str, int | str]:
    normalized_state = str(battle_state or "").upper().strip()
    if normalized_state not in {"RESOLVED", "DEFEATED"}:
        return {
            "quest_progress_delta": 0,
            "main_quest_progress_delta": 0,
            "demon_score_delta": 0,
            "result_label": "SKIPPED",
        }

    state = get_or_create_world_state(db, world_id)
    main_quest = get_main_quest(db, world_id)
    side_quest_001 = get_side_quest(db, world_id, "side_001")

    quest_progress_delta = 0
    main_quest_progress_delta = 0
    demon_score_delta = 0

    if normalized_state == "RESOLVED":
        if not main_quest or main_quest.status != "CLEARED":
            state.quest_progress += 1
            quest_progress_delta = 1
            if main_quest:
                main_quest.progress += 1
                main_quest_progress_delta = 1
                db.add(main_quest)
        state.security_score = clamp_security_score(state.security_score + 1)
    else:
        state.demon_score += 1
        demon_score_delta = 1
        state.security_score = clamp_security_score(state.security_score - 3)

    if not state.main_event_title:
        state.main_event_title = "北坑道の異変"
    if state.main_event_state != "CLEARED":
        state.main_event_state = "ACTIVE"

    apply_world_quest_completion_rules(
        db,
        world_id=world_id,
        state=state,
        main_quest=main_quest,
        side_quest_001=side_quest_001,
    )

    result_label = "勝利" if normalized_state == "RESOLVED" else "敗北"
    if quest_progress_delta > 0:
        body = (
            f"戦闘 {battle_id} の{result_label}により、クエスト進行が {quest_progress_delta} 進んだ。"
        )
    else:
        body = f"戦闘 {battle_id} は{result_label}で終わった。"

    db.add(
        Log(
            world_id=world_id,
            log_type="quest",
            title=f"戦闘決着: {result_label}",
            body=body,
        )
    )
    db.add(state)
    sync_security_side_quest(db, world_id=world_id, state=state)

    return {
        "quest_progress_delta": quest_progress_delta,
        "main_quest_progress_delta": main_quest_progress_delta,
        "demon_score_delta": demon_score_delta,
        "result_label": result_label,
    }
