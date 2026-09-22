from __future__ import annotations

from pathlib import Path

from insecured.pipeline.base import Stage, StageContext


class MountStage(Stage):
    """Étape 0 - montage du support / préparation de l'accès à l'image.

    Sur un poste Qubes, le bridge assure l'attachement du bloc (qvm-block) et
    expose le point de montage. En mode dev, vérifie simplement la présence du
    point de montage (dossier DEV_MEDIA).
    """

    name = "mount"

    def __init__(self, mount_point: str | Path = "DEV_MEDIA", bridge=None, device=None) -> None:
        self.mount_point = Path(mount_point)
        self.bridge = bridge
        self.device = device

    def run(self, ctx: StageContext) -> dict:
        mount = self.mount_point
        ctx.data["mount_point"] = str(mount)

        if self.bridge is not None and getattr(self.bridge, "available", True):
            try:
                attach = self.bridge.attach_block("analysis", self.device) if self.device else ""
                ctx.data["attach"] = attach
            except Exception as exc:
                return {"status": "warn", "message": f"attachement : {exc}"}

        if mount.exists():
            return {
                "status": "ok",
                "message": f"support prêt à {mount.resolve()}",
                "mount_point": str(mount),
            }

        return {
            "status": "warn",
            "message": f"point de montage absent : {mount}",
            "mount_point": str(mount),
        }