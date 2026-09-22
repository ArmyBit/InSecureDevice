from __future__ import annotations

import os
from pathlib import Path

from insecured.models.evidence import EvidenceFile
from insecured.pipeline.base import Stage, StageContext


class InventoryStage(Stage):
    """Stage 1 - inventaire des fichiers de l'image forensique.

    Parcourt le point de montage (lecture seule) de l'image et construit la
    liste des fichiers à analyser. En mode développement (sans Qubes), le
    point de montage pointe sur un répertoire de test.
    """

    name = "inventory"

    def __init__(self, mount_point: str | Path = "/mnt/evidence") -> None:
        self.mount_point = Path(mount_point)

    def run(self, ctx: StageContext) -> dict:
        root = self.mount_point
        if not root.exists():
            return {"status": "skip", "message": f"Montage inexistant : {root}", "files": []}

        files: list[EvidenceFile] = []
        skipped = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                if name.startswith("."):
                    skipped += 1
                    continue
                full = Path(dirpath) / name
                try:
                    stat = full.stat()
                except OSError:
                    files.append(EvidenceFile(path=full, notes="stat impossible"))
                    continue
                files.append(
                    EvidenceFile(path=full, size=stat.st_size, modified=datetime_from(stat.st_mtime))
                )
                self._report(f"Inventaire : {full}", None)
        files.sort(key=lambda f: f.path.as_posix())
        ctx.files = files
        return {
            "status": "ok" if files else "empty",
            "count": len(files),
            "skipped": skipped,
            "files": [f.to_dict() for f in files],
            "message": f"{len(files)} fichiers indexés",
        }


def datetime_from(ts: float):
    from datetime import datetime

    return datetime.fromtimestamp(ts)