from __future__ import annotations


TACTIC_KEYWORDS: dict[str, list[str]] = {
    "backlight": [
        "太陽を背に",
        "光を背に",
        "逆光",
        "日差しを利用",
        "眩しさを利用",
    ],
    "high_ground": [
        "段差の上",
        "高所",
        "上から",
        "見下ろして",
        "高台",
    ],
    "feint_attack": [
        "フェイント",
        "ふりをして",
        "誘って",
        "一度引いて",
        "引くふり",
    ],
    "mud_defense": [
        "ぬかるみ",
        "泥",
        "足を沈めて",
        "踏ん張って",
        "足場を固めて",
    ],
    "cover_use": [
        "壁際",
        "柱",
        "物陰",
        "遮蔽",
        "瓦礫の陰",
        "身を隠して",
    ],
}


def parse_tactic_tags(declared_tactic_text: str, max_tags: int = 2) -> list[str]:
    """
    自由記述の戦術宣言文から、簡易的に戦術タグを抽出する。
    最初はキーワード一致のみ。
    """
    if not declared_tactic_text:
        return []

    text = declared_tactic_text.strip()
    if not text:
        return []

    matched_tags: list[str] = []

    for tag_key, keywords in TACTIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                matched_tags.append(tag_key)
                break

    # 重複除去しつつ順序維持
    unique_tags: list[str] = []
    for tag in matched_tags:
        if tag not in unique_tags:
            unique_tags.append(tag)

    return unique_tags[:max_tags]