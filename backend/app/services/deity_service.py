from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app.models.world import World

PRIMARY_DOMAINS = [
    "戦", "弓", "癒し", "豊穣", "商", "火", "水", "風", "地", "光", "闇", "旅", "鍛冶", "境界"
]
SECONDARY_DOMAINS = [
    "誓約", "夜", "狩猟", "守護", "収穫", "巡礼", "星", "河川", "雷", "灰", "再生", "秩序"
]
SYMBOL_PARTS = {
    "core": ["輪", "剣", "弓", "杯", "穂", "秤", "炎", "月", "星", "鍵", "盾", "槌"],
    "accent": ["六芒", "双線", "滴", "枝", "冠", "羽", "鐘", "環", "爪", "角"],
}
NAME_PREFIXES = ["白枝", "灰鐘", "星紡", "燼冠", "青秤", "霧弦", "黎明", "夜環", "紅祷", "巡灯"]
NAME_SUFFIXES = ["神", "神君", "守", "大神", "導師", "聖主"]
DOCTRINE_TEMPLATES = [
    "{primary}と{secondary}を重んじ、弱き者を見捨てぬことを教義とする。",
    "{primary}の試練を越えてこそ、{secondary}の恩寵に届くと説く。",
    "{primary}は力でなく節度に宿り、{secondary}は日々の務めに現れるとされる。",
]
MYTH_TEMPLATES = [
    "かつて{primary}の火種を携え、荒れた地に{secondary}の道を開いたと伝わる。",
    "{secondary}を失った民へ{primary}のしるしを与え、最初の共同体を結ばせたという。",
    "王も盗賊も等しく裁き、最後には{primary}の象徴だけを残して去ったと語られる。",
]
RIVALRY_TEMPLATES = [
    "{other}の信徒とは巡礼路の扱いを巡って対立しがちだ。",
    "{other}の聖職者とは救済の解釈が噛み合わず、静かな競争関係にある。",
    "{other}の教会とは都市での布教順を巡って軋轢を抱える。",
]


def _build_symbol_mark(rng: random.Random) -> str:
    return f"{rng.choice(SYMBOL_PARTS['accent'])}の{rng.choice(SYMBOL_PARTS['core'])}"


def list_world_deities(db: Session, *, world: World, count: int = 3) -> list[dict[str, object]]:
    rng = random.Random(int(world.seed) * 401 + int(world.world_id) * 19)
    primary_domains = PRIMARY_DOMAINS.copy()
    secondary_domains = SECONDARY_DOMAINS.copy()
    rng.shuffle(primary_domains)
    rng.shuffle(secondary_domains)

    deities: list[dict[str, object]] = []
    for index in range(count):
        primary = primary_domains[index % len(primary_domains)]
        secondary = secondary_domains[index % len(secondary_domains)]
        name = f"{rng.choice(NAME_PREFIXES)}の{primary}{rng.choice(NAME_SUFFIXES)}"
        deity_key = f"deity_{index+1:03d}_{primary}"
        doctrine = rng.choice(DOCTRINE_TEMPLATES).format(primary=primary, secondary=secondary)
        myth = rng.choice(MYTH_TEMPLATES).format(primary=primary, secondary=secondary)
        deities.append(
            {
                "deity_key": deity_key,
                "name": name,
                "domains": [primary, secondary],
                "symbol_mark": _build_symbol_mark(rng),
                "doctrine_summary": doctrine,
                "myth_fragment": myth,
                "church_name": f"{name}の教会",
            }
        )

    for index, deity in enumerate(deities):
        other = deities[(index + 1) % len(deities)]["name"] if len(deities) > 1 else "他宗派"
        deity["rivalry_hint"] = rng.choice(RIVALRY_TEMPLATES).format(other=other)
    return deities


def list_religious_rumors(db: Session, *, world: World, limit: int = 2) -> list[str]:
    rumors: list[str] = []
    for deity in list_world_deities(db, world=world, count=max(limit, 3))[:limit]:
        rumors.append(f"{deity['church_name']}では『{deity['myth_fragment']}』という説話がよく語られている。")
    return rumors
