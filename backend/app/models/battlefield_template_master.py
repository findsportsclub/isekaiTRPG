from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BattlefieldTemplateMaster(Base):
    __tablename__ = "battlefield_template_master"

    template_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    template_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False, default="")

    terrain_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )
    environment_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )
    movement_rules_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )
    tactical_bias_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    default_objective_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    psychological_effect: Mapped[str] = mapped_column(Text, nullable=False, default="")
    symbolism_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    gm_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suitable_roles_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    enabled_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)