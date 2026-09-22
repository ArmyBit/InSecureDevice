from __future__ import annotations

import hashlib

from insecured.pipeline.base import Stage, StageContext


class HashStage(Stage):
    """Stage 2 - extraction des empreintes SHA-256 de chaque fichier."""

    name = "hashing"

    def __init__(self, chunk_size: int = 1 << 20) -> None:
        self.chunk_size = chunk_size

    def run(self, ctx: StageContext) -> dict:
        done = 0
        total = len(ctx.files)
        for f in ctx.files:
            f.sha256 = self._digest(f.path)
            done += 1
            self._report(f"Hachage : {f.path.name} ({done}/{total})", done * 100 // max(total, 1))
        return {"status": "ok", "hashed": sum(1 for f in ctx.files if f.sha256)}

    @staticmethod
    def _digest(path) -> str:
        h = hashlib.sha256()
        try:
            with open(path, "rb") as fh:
                for block in iter(lambda: fh.read(1 << 20), b""):
                    h.update(block)
        except OSError:
            return ""
        return h.hexdigest()