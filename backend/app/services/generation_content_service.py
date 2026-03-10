from __future__ import annotations

import ast
import json
import random
from pathlib import Path
from typing import Any

from app.services.battle_registry import EquipmentDefinition, register_equipment

_CACHE: dict[str, dict[str, Any]] = {}

NAMING_PACK_CANDIDATES = [
    Path.home() / "Downloads" / "trpg_naming_codex_pack.json",
]

MAGIC_PACK_CANDIDATES = [
    Path.home() / "Downloads" / "trpg_magic_system_for_codex.json",
]

FALLBACK_NAMING_PACK = {
    "genres": {
        "high_fantasy": {
            "label": "ハイファンタジー",
            "naming_parts": {
                "prefixes": ["星の", "白銀の", "祝福の"],
                "cores": ["外套", "指環", "胸甲", "護符", "兜"],
                "suffixes": ["守護", "神託", "風歌"],
            },
            "naming_patterns": ["{prefix}{core}", "{prefix}{core}・{suffix}"],
            "effect_tables": {
                "main": ["属性付与", "結界展開", "味方支援"],
                "sub": ["詠唱短縮", "士気上昇", "魔力効率上昇"],
                "cost": ["契約者限定", "詠唱必須", "一定時間準備必要"],
            },
        }
    }
}

FALLBACK_MAGIC_PACK = {
    "preset_spells": [],
    "attributes": [],
}


def _load_json_file(candidates: list[Path], fallback_key: str, fallback_data: dict[str, Any]) -> dict[str, Any]:
    if fallback_key in _CACHE:
        return _CACHE[fallback_key]
    for path in candidates:
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                _CACHE[fallback_key] = data
                return data
        except Exception:
            try:
                raw = path.read_text(encoding="utf-8")
                marker = "data ="
                if marker in raw:
                    expr = raw.split(marker, 1)[1]
                    if "\nout =" in expr:
                        expr = expr.split("\nout =", 1)[0]
                    elif "Path(" in expr and ").write_text" in expr:
                        expr = expr.split("Path(", 1)[0]
                    data = ast.literal_eval(expr.strip())
                    if isinstance(data, dict):
                        _CACHE[fallback_key] = data
                        return data
            except Exception:
                continue
    _CACHE[fallback_key] = fallback_data
    return fallback_data


def load_naming_pack() -> dict[str, Any]:
    return _load_json_file(NAMING_PACK_CANDIDATES, "naming_pack", FALLBACK_NAMING_PACK)


def load_magic_pack() -> dict[str, Any]:
    return _load_json_file(MAGIC_PACK_CANDIDATES, "magic_pack", FALLBACK_MAGIC_PACK)


def _select_genre(seed: int) -> tuple[str, dict[str, Any]]:
    pack = load_naming_pack()
    genres = dict(pack.get("genres", {}) or {})
    if not genres:
        genres = dict(FALLBACK_NAMING_PACK["genres"])
    genre_keys = sorted(genres.keys())
    genre_key = genre_keys[seed % len(genre_keys)]
    return genre_key, dict(genres[genre_key] or {})


def _build_name(rng: random.Random, genre: dict[str, Any]) -> tuple[str, str]:
    parts = dict(genre.get("naming_parts", {}) or {})
    prefixes = list(parts.get("prefixes", []) or ["古びた"])
    cores = list(parts.get("cores", []) or ["護符"])
    suffixes = list(parts.get("suffixes", []) or ["守護"])
    patterns = list(genre.get("naming_patterns", []) or ["{prefix}{core}"])
    pattern = str(patterns[rng.randrange(len(patterns))])
    name = (
        pattern.replace("{prefix}", str(prefixes[rng.randrange(len(prefixes))]))
        .replace("{core}", str(cores[rng.randrange(len(cores))]))
        .replace("{suffix}", str(suffixes[rng.randrange(len(suffixes))]))
    )
    return name, pattern


def _derive_slot_type(name: str, item_type: str) -> str:
    if item_type == "armor":
        if any(token in name for token in ["指環", "首飾", "護符", "腕輪", "肩飾り"]):
            return "accessory"
        if any(token in name for token in ["兜", "冠", "額冠", "仮面"]):
            return "head"
        if any(token in name for token in ["外套", "法衣", "衣"]):
            return "armor"
        return "armor"
    if item_type == "artifact":
        return "accessory"
    return "accessory"


def _derive_bonuses(main_effect: str, sub_effect: str, rarity: str, slot_type: str) -> dict[str, int]:
    scale = {"COMMON": 1, "RARE": 2, "EPIC": 3, "LEGENDARY": 4}.get(rarity, 1)
    bonuses = {
        "atk_bonus": 0,
        "defense_bonus": 0,
        "mag_bonus": 0,
        "res_bonus": 0,
        "spd_bonus": 0,
        "hit_bonus": 0,
        "eva_bonus": 0,
        "crit_bonus": 0,
    }
    if "結界" in main_effect or "防御" in main_effect:
        bonuses["defense_bonus"] += scale + (1 if slot_type == "armor" else 0)
        bonuses["res_bonus"] += max(1, scale - 1)
    if "支援" in main_effect or "祝福" in main_effect or "浄化" in main_effect:
        bonuses["mag_bonus"] += scale
        bonuses["res_bonus"] += 1
    if "属性" in main_effect or "精霊" in main_effect:
        bonuses["mag_bonus"] += scale
        bonuses["hit_bonus"] += 1
    if "士気" in sub_effect:
        bonuses["defense_bonus"] += 1
    if "詠唱短縮" in sub_effect or "魔力効率" in sub_effect:
        bonuses["mag_bonus"] += 1
        bonuses["spd_bonus"] += 1
    if "飛行" in sub_effect or "罠感知" in sub_effect:
        bonuses["eva_bonus"] += 1
    return bonuses


def _derive_offer_cost(rarity: str, slot_type: str) -> int:
    base = {"COMMON": 18, "RARE": 42, "EPIC": 90, "LEGENDARY": 180}.get(rarity, 18)
    if slot_type == "accessory":
        return base + 8
    if slot_type == "head":
        return base + 5
    return base + 12


def build_market_offers(*, world_seed: int, security_score: int, count: int = 3) -> list[dict[str, Any]]:
    genre_key, genre = _select_genre(world_seed + security_score)
    magic_pack = load_magic_pack()
    rng = random.Random(world_seed * 131 + security_score * 17 + count)
    item_type_cycle = ["armor", "artifact", "armor", "artifact"]
    rarities = ["COMMON", "RARE", "EPIC"]
    effects = dict(genre.get("effect_tables", {}) or {})
    main_effects = list(effects.get("main", []) or ["味方支援"])
    sub_effects = list(effects.get("sub", []) or ["士気上昇"])
    costs = list(effects.get("cost", []) or ["契約者限定"])
    attributes = list(magic_pack.get("attributes", []) or [])
    items: list[dict[str, Any]] = []
    for index in range(count):
        item_type = item_type_cycle[index % len(item_type_cycle)]
        rarity = rarities[min(index, len(rarities) - 1)]
        name, pattern = _build_name(rng, genre)
        main_effect = str(main_effects[rng.randrange(len(main_effects))])
        sub_effect = str(sub_effects[rng.randrange(len(sub_effects))])
        drawback = str(costs[rng.randrange(len(costs))])
        attribute = dict(attributes[rng.randrange(len(attributes))]) if attributes else {}
        attribute_name = str(attribute.get("name", "無属性"))
        slot_type = _derive_slot_type(name, item_type)
        key = f"market_{world_seed}_{index}_{genre_key}_{slot_type}".lower()
        bonuses = _derive_bonuses(main_effect, sub_effect, rarity, slot_type)
        items.append(
            {
                "offer_key": key,
                "equipment_key": key,
                "name": name,
                "pattern_used": pattern,
                "genre_id": genre_key,
                "item_type": item_type,
                "slot_type": slot_type,
                "rarity": rarity,
                "main_effect": main_effect,
                "sub_effect": sub_effect,
                "attribute_hint": attribute_name,
                "cost_text": drawback,
                "price_gold": _derive_offer_cost(rarity, slot_type),
                "bonuses": bonuses,
                "flavor_text": f"{attribute_name}の気配と{main_effect}を帯び、{sub_effect}にも触れるが、{drawback}という癖を持つ。",
            }
        )
    return items


def register_market_equipment(offer: dict[str, Any]) -> EquipmentDefinition:
    bonuses = dict(offer.get("bonuses", {}) or {})
    equipment = EquipmentDefinition(
        equipment_key=str(offer["equipment_key"]),
        name=str(offer["name"]),
        slot_type=str(offer["slot_type"]),
        atk_bonus=int(bonuses.get("atk_bonus", 0) or 0),
        defense_bonus=int(bonuses.get("defense_bonus", 0) or 0),
        mag_bonus=int(bonuses.get("mag_bonus", 0) or 0),
        res_bonus=int(bonuses.get("res_bonus", 0) or 0),
        spd_bonus=int(bonuses.get("spd_bonus", 0) or 0),
        hit_bonus=int(bonuses.get("hit_bonus", 0) or 0),
        eva_bonus=int(bonuses.get("eva_bonus", 0) or 0),
        crit_bonus=int(bonuses.get("crit_bonus", 0) or 0),
        effect_list=[],
        tags=[
            str(offer.get("genre_id", "generated")),
            str(offer.get("item_type", "artifact")),
            str(offer.get("slot_type", "accessory")),
            "generated_market",
        ],
        rarity=str(offer.get("rarity", "COMMON")),
        flavor_text=str(offer.get("flavor_text", "")),
        generated_by_ai=False,
        validation_status="VALID",
    )
    register_equipment(equipment, overwrite=True)
    return equipment


def get_market_offer_by_key(*, world_seed: int, security_score: int, offer_key: str) -> dict[str, Any] | None:
    for item in build_market_offers(world_seed=world_seed, security_score=security_score, count=4):
        if str(item.get("offer_key", "")) == str(offer_key):
            return item
    return None


def build_blessing_offers(*, world_seed: int, count: int = 3) -> list[dict[str, Any]]:
    magic_pack = load_magic_pack()
    naming_pack = load_naming_pack()
    attributes = list(magic_pack.get("attributes", []) or [])
    genre_keys = sorted(dict(naming_pack.get("genres", {}) or {}).keys()) or ["high_fantasy"]
    rng = random.Random(world_seed * 211 + count)
    offers: list[dict[str, Any]] = []
    for index in range(count):
        attribute = dict(attributes[rng.randrange(len(attributes))]) if attributes else {"id": "light_heal", "name": "光／回復", "keywords": ["光", "加護"]}
        genre_key = genre_keys[index % len(genre_keys)]
        blessing_key = f"blessing_{world_seed}_{index}_{attribute.get('id', 'light')}"
        offers.append(
            {
                "blessing_key": blessing_key,
                "name": f"{attribute.get('name', '光')}の恩寵",
                "domain": str(attribute.get("name", "光／回復")),
                "source_hint": genre_key,
                "effect_tags": list(attribute.get("keywords", [])[:3] or ["加護"]),
                "grant_type": "passive",
                "summary": f"{attribute.get('name', '光／回復')}に紐づく加護。探索や戦闘で穏やかな補助を与える。",
            }
        )
    return offers


def build_authority_candidates(*, world_seed: int, count: int = 3) -> list[dict[str, Any]]:
    naming_pack = load_naming_pack()
    genre_keys = sorted(dict(naming_pack.get("genres", {}) or {}).keys()) or ["high_fantasy"]
    rng = random.Random(world_seed * 307 + count)
    authority_classes = [
        ("rewrite", "局所改変"),
        ("continuity", "継承固定"),
        ("sanctify", "加護転写"),
        ("observe", "因果観測"),
    ]
    targets = ["self", "party", "area", "continuity"]
    items: list[dict[str, Any]] = []
    for index in range(count):
        authority_class, label = authority_classes[index % len(authority_classes)]
        genre_key = genre_keys[rng.randrange(len(genre_keys))]
        authority_key = f"authority_{world_seed}_{index}_{authority_class}"
        items.append(
            {
                "authority_key": authority_key,
                "name": f"{label}・{genre_key}",
                "authority_class": authority_class,
                "scope": targets[index % len(targets)],
                "rule_break_level": "mid" if index < 2 else "high",
                "summary": "世界法則へ局所的な例外を作る義認権能候補。",
            }
        )
    return items
