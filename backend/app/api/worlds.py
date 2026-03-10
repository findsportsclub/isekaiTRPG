from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.models.world import World
from app.models.log import Log
from app.models.world_state import WorldState
from app.models.quest import Quest
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.world import (
    WorldListItem,
    WorldListResponse,
    WorldDetailResponse,
    CrisisScores,
    MainEvent,
    WorldCreateRequest,
    WorldCreateResponse,
)
from app.schemas.action import (
    ActionListResponse,
    ActionItem,
    NearbyNpc,
    NearbyEvent,
    MoveDestination,
    ActionExecuteRequest,
    ActionExecuteResponse,
)
from app.schemas.log import LogItem, LogListResponse
from app.schemas.quest import QuestItem, QuestListResponse
from app.services.world_progress_service import (
    get_or_create_world_state,
    apply_world_quest_completion_rules,
    build_security_rumors,
)
from app.services.campaign_phase_service import get_or_create_campaign_state
from app.services.relationship_service import apply_relationship_delta
from app.services.tendency_service import apply_tendency_delta, get_or_create_tendency_state

router = APIRouter(prefix="/api", tags=["worlds"])


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == request.email).first()

        if not user:
            username = request.email.split("@")[0]
            user = User(
                email=request.email,
                username=username,
                password_hash="dummy_hash",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        return LoginResponse(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
        )
    finally:
        db.close()


@router.get("/worlds", response_model=WorldListResponse)
def list_worlds():
    db: Session = SessionLocal()
    try:
        worlds = db.query(World).all()
        items = [
            WorldListItem(
                world_id=w.world_id,
                world_name=w.world_name,
                hero_name=w.hero_name,
                era=w.era,
                current_location=w.current_location,
            )
            for w in worlds
        ]
        return WorldListResponse(worlds=items)
    finally:
        db.close()


@router.get("/users/{user_id}/worlds", response_model=WorldListResponse)
def list_user_worlds(user_id: int):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        worlds = (
            db.query(World)
            .filter(World.owner_user_id == user_id)
            .order_by(World.world_id.desc())
            .all()
        )

        items = [
            WorldListItem(
                world_id=w.world_id,
                world_name=w.world_name,
                hero_name=w.hero_name,
                era=w.era,
                current_location=w.current_location,
            )
            for w in worlds
        ]
        return WorldListResponse(worlds=items)
    finally:
        db.close()


@router.post("/worlds", response_model=WorldCreateResponse)
def create_world(request: WorldCreateRequest):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_world = World(
            owner_user_id=request.user_id,
            world_name=request.world_name,
            hero_name=request.hero_name,
            seed=request.seed,
            era="DUNGEON_AGE",
            current_location="はじまりの村",
        )
        db.add(new_world)
        db.commit()
        db.refresh(new_world)

        new_state = WorldState(
            world_id=new_world.world_id,
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
        db.add(new_state)
        db.commit()

        main_quest = Quest(
            world_id=new_world.world_id,
            quest_id="main_001",
            category="main",
            title="北坑道の異変",
            status="ACTIVE",
            description="北坑道周辺で起きている異変の正体を探る。",
            progress=0,
        )
        db.add(main_quest)
        db.commit()

        get_or_create_campaign_state(db, new_world.world_id)
        get_or_create_tendency_state(db, world_id=new_world.world_id)
        db.commit()

        return WorldCreateResponse(
            world_id=new_world.world_id,
            world_name=new_world.world_name,
            hero_name=new_world.hero_name,
            era=new_world.era,
            current_location=new_world.current_location,
        )
    finally:
        db.close()


@router.get("/worlds/{world_id}", response_model=WorldDetailResponse)
def get_world_detail(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        state = get_or_create_world_state(db, world_id)
        db.commit()
        db.refresh(state)

        return WorldDetailResponse(
            world_id=world.world_id,
            world_name=world.world_name,
            hero_name=world.hero_name,
            era=world.era,
            current_location=world.current_location,
            crisis_scores=CrisisScores(
                dungeon=state.dungeon_score,
                faction=state.faction_score,
                demon=state.demon_score,
                security=state.security_score,
            ),
            main_event=MainEvent(
                title=state.main_event_title,
                state=state.main_event_state,
                progress=state.quest_progress,
            ),
            recent_rumors=[
                "北で霧が濃くなっている",
                "坑道で失踪者が出た",
                *build_security_rumors(state),
            ][:4],
        )
    finally:
        db.close()


@router.get("/worlds/{world_id}/actions", response_model=ActionListResponse)
def get_world_actions(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        move_map = {
            "はじまりの村": [
                MoveDestination(location_id="village_gate", label="村の入口"),
                MoveDestination(location_id="inn", label="宿屋"),
            ],
            "村の入口": [
                MoveDestination(location_id="start_village", label="はじまりの村"),
                MoveDestination(location_id="north_mine", label="北坑道前"),
            ],
            "北坑道前": [
                MoveDestination(location_id="village_gate", label="村の入口"),
            ],
            "宿屋": [
                MoveDestination(location_id="start_village", label="はじまりの村"),
            ],
        }

        if world.current_location == "はじまりの村":
            nearby_npcs = [
                NearbyNpc(npc_id="npc_001", name="村長"),
                NearbyNpc(npc_id="npc_002", name="宿屋の主人"),
            ]
            nearby_events = [NearbyEvent(event_id="ev_001", title="北坑道の噂")]
        elif world.current_location == "村の入口":
            nearby_npcs = [NearbyNpc(npc_id="npc_003", name="見張りの青年")]
            nearby_events = [NearbyEvent(event_id="ev_002", title="街道の足跡")]
        elif world.current_location == "北坑道前":
            nearby_npcs = [NearbyNpc(npc_id="npc_004", name="鉱夫の老人")]
            nearby_events = [NearbyEvent(event_id="ev_003", title="坑道からの異音")]
        elif world.current_location == "宿屋":
            nearby_npcs = [
                NearbyNpc(npc_id="npc_002", name="宿屋の主人"),
                NearbyNpc(npc_id="npc_005", name="旅人"),
            ]
            nearby_events = [NearbyEvent(event_id="ev_004", title="旅人の噂話")]
        else:
            nearby_npcs = []
            nearby_events = []

        return ActionListResponse(
            location=world.current_location,
            time_label="朝",
            actions=[
                ActionItem(action_id="talk", label="話す"),
                ActionItem(action_id="inspect", label="調べる"),
                ActionItem(action_id="move", label="移動する"),
                ActionItem(action_id="rest", label="休む"),
            ],
            nearby_npcs=nearby_npcs,
            nearby_events=nearby_events,
            move_destinations=move_map.get(world.current_location, []),
        )
    finally:
        db.close()


@router.post("/worlds/{world_id}/actions/execute", response_model=ActionExecuteResponse)
def execute_world_action(world_id: int, request: ActionExecuteRequest):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        state = get_or_create_world_state(db, world_id)
        db.commit()
        db.refresh(state)

        main_quest = (
            db.query(Quest)
            .filter(Quest.world_id == world_id, Quest.category == "main")
            .first()
        )
        side_quest_001 = (
            db.query(Quest)
            .filter(Quest.world_id == world_id, Quest.quest_id == "side_001")
            .first()
        )

        if request.action_id == "talk":
            if not request.target_npc_id:
                summary = "話しかける相手が選ばれていない。"
                result_type = "none"
            elif request.target_npc_id == "npc_001":
                summary = "村長は、北坑道の霧が日ごとに濃くなっていると語った。"
                result_type = "info"
                state.faction_score += 1
                state.quest_progress += 1
                if main_quest:
                    main_quest.progress += 1
            elif request.target_npc_id == "npc_002":
                summary = "宿屋の主人は、坑道へ向かった旅人が戻っていないと教えてくれた。"
                result_type = "rumor"
                state.demon_score += 1
                state.quest_progress += 1
                if main_quest:
                    main_quest.progress += 1
            elif request.target_npc_id == "npc_003":
                summary = "見張りの青年は、夜明け前に街道を横切る影を見たと話した。"
                result_type = "info"
                state.faction_score += 1
                state.quest_progress += 1
                if main_quest:
                    main_quest.progress += 1
            elif request.target_npc_id == "npc_004":
                summary = "鉱夫の老人は、坑道の奥から金属を擦るような音が聞こえたと言った。"
                result_type = "warning"
                state.dungeon_score += 1
                state.quest_progress += 1
                if main_quest:
                    main_quest.progress += 1
            elif request.target_npc_id == "npc_005":
                summary = "旅人は、宿で聞いた噂として『坑道には地図にない横穴がある』と囁いた。"
                result_type = "rumor"
                state.dungeon_score += 1
                state.quest_progress += 1
                if main_quest:
                    main_quest.progress += 1
            else:
                summary = "その相手とはうまく話せなかった。"
                result_type = "none"

            if request.target_npc_id:
                trust_delta = 0.05
                affinity_delta = 0.04
                if (request.attitude_tone or "").lower() in {"cold", "threatening", "hostile"}:
                    trust_delta -= 0.06
                    affinity_delta -= 0.05
                elif (request.attitude_tone or "").lower() in {"kind", "gentle", "honest"}:
                    trust_delta += 0.04
                    affinity_delta += 0.03
                if (request.intent_tag or "").lower() in {"probe", "pressure"}:
                    affinity_delta -= 0.03

                apply_relationship_delta(
                    db,
                    world_id=world_id,
                    target_key=request.target_npc_id,
                    interaction_type="talk",
                    trust_delta=trust_delta,
                    affinity_delta=affinity_delta,
                )

            tendency_delta = {"honest": 1, "protective": 1}
            if (request.attitude_tone or "").lower() in {"cold", "threatening", "hostile"}:
                tendency_delta = {"pragmatic": 1, "bold": 1}
            elif (request.intent_tag or "").lower() in {"probe", "information"}:
                tendency_delta = {"curious": 1, "cautious": 1}
            apply_tendency_delta(
                db,
                world_id=world_id,
                reason="world_action:talk",
                deltas=tendency_delta,
            )

        elif request.action_id == "inspect":
            if world.current_location == "はじまりの村":
                summary = "掲示板を調べると、北坑道の見回り依頼が貼られていた。"
                result_type = "discovery"
                state.dungeon_score += 1
                state.quest_progress += 1
                state.main_event_title = "北坑道の見回り依頼"
                state.main_event_state = "ACTIVE"
                if main_quest:
                    main_quest.progress += 1
            elif world.current_location == "村の入口":
                summary = "地面を調べると、村の外へ向かう新しい足跡がいくつも見つかった。"
                result_type = "discovery"
                state.dungeon_score += 2
                state.quest_progress += 1
                state.main_event_title = "街道に残された足跡"
                state.main_event_state = "ACTIVE"
                if main_quest:
                    main_quest.progress += 1
            elif world.current_location == "北坑道前":
                summary = "坑道の入口には、爪で削ったような深い傷跡が残っていた。さらに壁際に、不自然に風が流れ込む裂け目を見つけた。"
                result_type = "discovery"
                state.dungeon_score += 3
                state.quest_progress += 2
                state.main_event_title = "坑道入口の異変"
                state.main_event_state = "ACTIVE"
                if main_quest:
                    main_quest.progress += 2
                if side_quest_001 and side_quest_001.status != "CLEARED":
                    side_quest_001.progress += 1
                    if side_quest_001.progress >= 2:
                        side_quest_001.status = "CLEARED"
            elif world.current_location == "宿屋":
                summary = "宿の片隅に置かれた荷の中に、坑道の地図の切れ端を見つけた。未探索の横穴があるようだ。"
                result_type = "discovery"
                state.faction_score += 1
                state.quest_progress += 1
                state.main_event_title = "坑道の横穴に関する手がかり"
                state.main_event_state = "ACTIVE"
                if main_quest:
                    main_quest.progress += 1
                if not side_quest_001:
                    side_quest_001 = Quest(
                        world_id=world_id,
                        quest_id="side_001",
                        category="side",
                        title="坑道の横穴を調べる",
                        status="ACTIVE",
                        description="宿で見つけた地図の切れ端を手がかりに、坑道の横穴の存在を確かめる。",
                        progress=0,
                    )
                    db.add(side_quest_001)
            else:
                summary = "周囲を調べたが、目立った発見はなかった。"
                result_type = "none"

            apply_tendency_delta(
                db,
                world_id=world_id,
                reason="world_action:inspect",
                deltas={"curious": 1, "cautious": 1},
            )

        elif request.action_id == "move":
            destination_map = {
                "start_village": "はじまりの村",
                "village_gate": "村の入口",
                "north_mine": "北坑道前",
                "inn": "宿屋",
            }
            if not request.target_location:
                summary = "移動先が選ばれていない。"
                result_type = "none"
            else:
                next_location = destination_map.get(request.target_location)
                if not next_location:
                    summary = "不明な移動先が指定された。"
                    result_type = "none"
                else:
                    world.current_location = next_location
                    summary = f"{next_location}へ移動した。"
                    result_type = "movement"

                    move_delta = {"bold": 1}
                    if request.target_location == "north_mine":
                        move_delta["cautious"] = 1
                    apply_tendency_delta(
                        db,
                        world_id=world_id,
                        reason="world_action:move",
                        deltas=move_delta,
                    )

        elif request.action_id == "rest":
            summary = "宿で休み、体勢を整えた。"
            result_type = "recovery"
            state.demon_score = max(0, state.demon_score - 1)
            apply_tendency_delta(
                db,
                world_id=world_id,
                reason="world_action:rest",
                deltas={"cautious": 1, "protective": 1},
            )

        else:
            summary = "何も起こらなかった。"
            result_type = "none"

        apply_world_quest_completion_rules(
            db,
            world_id=world_id,
            state=state,
            main_quest=main_quest,
            side_quest_001=side_quest_001,
        )

        action_label_map = {
            "talk": "話す",
            "inspect": "調べる",
            "move": "移動する",
            "rest": "休む",
        }

        log = Log(
            world_id=world.world_id,
            log_type="action",
            title=f"行動: {action_label_map.get(request.action_id, request.action_id)}",
            body=summary,
        )
        db.add(log)
        db.commit()

        return ActionExecuteResponse(
            summary=summary,
            result_type=result_type,
        )
    finally:
        db.close()


@router.get("/worlds/{world_id}/logs", response_model=LogListResponse)
def list_world_logs(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        logs = (
            db.query(Log)
            .filter(Log.world_id == world_id)
            .order_by(Log.log_id.desc())
            .all()
        )

        return LogListResponse(
            logs=[
                LogItem(
                    log_id=log.log_id,
                    log_type=log.log_type,
                    title=log.title,
                    body=log.body,
                )
                for log in logs
            ]
        )
    finally:
        db.close()


@router.get("/worlds/{world_id}/quests", response_model=QuestListResponse)
def list_world_quests(world_id: int):
    db: Session = SessionLocal()
    try:
        world = db.query(World).filter(World.world_id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        quests = (
            db.query(Quest)
            .filter(Quest.world_id == world_id)
            .order_by(Quest.quest_row_id.asc())
            .all()
        )

        return QuestListResponse(
            quests=[
                QuestItem(
                    quest_id=quest.quest_id,
                    category=quest.category,
                    title=quest.title,
                    status=quest.status,
                    description=quest.description,
                    progress=quest.progress,
                )
                for quest in quests
            ]
        )
    finally:
        db.close()
