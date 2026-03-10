from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TacticTagMaster(Base):
    __tablename__ = "tactic_tag_master"

    tag_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    tag_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    category: Mapped[str] = mapped_column(String(50), nullable=False, default="TERRAIN")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="LOW")

    allowed_action_types_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='["ATTACK"]',
    )

    condition_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    effect_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    stack_rule: Mapped[str] = mapped_column(String(50), nullable=False, default="NO_STACK")
    enabled_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)