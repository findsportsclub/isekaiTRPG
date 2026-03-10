import json
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BattlefieldGimmick(Base):
    __tablename__ = "battlefield_gimmicks"

    gimmick_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    battlefield_id: Mapped[int] = mapped_column(
        ForeignKey("battlefields.battlefield_id"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False, default="TURN_ELAPSED")
    trigger_detail_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    effect_type: Mapped[str] = mapped_column(String(50), nullable=False, default="DAMAGE")
    effect_detail_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    beneficiary: Mapped[str] = mapped_column(String(20), nullable=False, default="BOTH")
    repeat_rule: Mapped[str] = mapped_column(String(30), nullable=False, default="ONCE")

    visual_description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    enabled_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def read_trigger_detail(self) -> dict[str, Any]:
        try:
            data = json.loads(self.trigger_detail_json)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def read_effect_detail(self) -> dict[str, Any]:
        try:
            data = json.loads(self.effect_detail_json)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}
