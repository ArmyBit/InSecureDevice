from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class EvidenceFile:
    """Un fichier individuel analysé à partir de l'image forensique."""

    path: Path
    size: int = 0
    sha256: str = ""
    magic: str = ""
    mime: str = ""
    created: datetime | None = None
    modified: datetime | None = None
    accessed: datetime | None = None
    anom: str = ""
    notes: str = ""
    vt: str = ""

    @property
    def is_suspicious(self) -> bool:
        return bool(self.anom)

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "size": self.size,
            "sha256": self.sha256,
            "magic": self.magic,
            "mime": self.mime,
            "created": self.created.isoformat() if self.created else None,
            "modified": self.modified.isoformat() if self.modified else None,
            "accessed": self.accessed.isoformat() if self.accessed else None,
            "anomaly": self.anom,
            "notes": self.notes,
            "vt": self.vt,
        }