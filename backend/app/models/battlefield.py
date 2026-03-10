import json
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Battlefield(Base):
    __tablename__ = "battlefields"

    battlefield_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    world_id: Mapped[int] = mapped_column(
        ForeignKey("worlds.world_id"),
        nullable=False,
        index=True,
    )

    location_id: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
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

    objective_type: Mapped[str] = mapped_column(String(50), nullable=False, default="DEFEAT")
    objective_detail_json: Mapped[str] = mapped_column(
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

    meaning_for_protagonist: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meaning_for_enemy: Mapped[str] = mapped_column(Text, nullable=False, default="")

    gm_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    time_progression_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    def read_environment(self) -> dict[str, Any]:
        try:
            data = json.loads(self.environment_json)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def write_environment(self, environment: dict[str, Any]) -> None:
        self.environment_json = json.dumps(environment, ensure_ascii=False)
