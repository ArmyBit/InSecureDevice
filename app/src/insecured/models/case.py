from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass
class Case:
    """Un cas d'analyse forensique.

    Regroupe les informations d'identification d'un cas, le chemin de l'image
    forensique analysée et l'historique des étapes de pipeline exécutées.
    """

    name: str
    image_path: Path
    case_id: str = field(default_factory=lambda: uuid4().hex[:12])
    operator: str = ""
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None

    def open(self) -> str:
        return (
            f"Case {self.case_id} - {self.name}\n"
            f"Opérateur : {self.operator or 'inconnu'}\n"
            f"Ouvert le : {self.opened_at.isoformat()}"
        )

    def close(self) -> None:
        self.closed_at = datetime.now(timezone.utc)