from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PipelineResult:
    """Résultat d'une étape (stage) de la pipeline."""

    stage: str
    status: str = "ok"
    message: str = ""
    data: dict = field(default_factory=dict)
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "at": self.at.isoformat(),
        }