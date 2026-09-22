from __future__ import annotations

from pathlib import Path

from insecured.pipeline.base import Stage, StageContext

_MAGIC_HEADERS = [
    (b"\x89PNG\r\n\x1a\n", "PNG image", "image/png"),
    (b"\xff\xd8\xff", "JPEG image", "image/jpeg"),
    (b"%PDF-", "PDF document", "application/pdf"),
    (b"PK\x03\x04", "ZIP archive", "application/zip"),
    (b"\x7fELF", "ELF executable", "application/x-executable"),
    (b"MZ", "PE executable (Windows)", "application/x-dosexec"),
    (b"GIF87a", "GIF image", "image/gif"),
    (b"GIF89a", "GIF image", "image/gif"),
    (b"BM", "BMP image", "image/bmp"),
]


class MetadataStage(Stage):
    """Stage 3 - lecture des métadonnées et des signatures magiques.

    Détermine le type réel d'un fichier par son nombre magique (bytes de tête)
    et compare avec l'extension. Consigne la taille et les dates utiles.
    """

    name = "metadata"

    def read_magic(self, path: Path, length: int = 16) -> bytes:
        try:
            with open(path, "rb") as fh:
                return fh.read(length)
        except OSError:
            return b""

    def classify(self, path: Path) -> tuple[str, str]:
        header = self.read_magic(path)
        for sig, desc, mime in _MAGIC_HEADERS:
            if header.startswith(sig):
                return desc, mime
        if header:
            return "Données inconnues", "application/octet-stream"
        return "Fichier vide", ""

    def run(self, ctx: StageContext) -> dict:
        mismatches = 0
        for f in ctx.files:
            desc, mime = self.classify(f.path)
            f.magic = desc
            f.mime = mime
            ext = f.path.suffix.lower().lstrip(".")
            if mime and ext and self._ext_mismatch(mime, ext):
                mismatches += 1
                f.anom = "extension/type incohérent"
                ctx.data.setdefault("mismatches", []).append(str(f.path))
            self._report(f"Métadonnées : {f.path.name}", None)
        return {"status": "ok", "extension_mismatches": mismatches}

    @staticmethod
    def _ext_mismatch(mime: str, ext: str) -> bool:
        if "image" in mime:
            return False  # les images ont des nombres magiques fiables
        if ext in ("pdf", "zip", "gz", "exe"):
            return ext not in mime
        return False