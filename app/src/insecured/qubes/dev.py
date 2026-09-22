from __future__ import annotations

from pathlib import Path

from insecured.qubes.base import QubesBridge, QubesDevice


class DevBridge(QubesBridge):
    """Bridge de développement.

    S'exécute hors d'un poste Qubes (Windows/station de dev) : aucun appel à
    qvm-block. Le "média connecté" est simulé par la présence d'un dossier
    DEV_MEDIA dans le répertoire de travail, ou d'un chemin fourni en paramètre.
    """

    def __init__(self, media_root: str | Path = "DEV_MEDIA") -> None:
        self.media_root = Path(media_root)

    @property
    def available(self) -> bool:
        return True

    def list_devices(self) -> list[QubesDevice]:
        if not self.media_root.exists():
            return []
        entries = [
            QubesDevice(bus_id=p.name, label=p.name)
            for p in self.media_root.iterdir()
            if p.is_dir()
        ]
        return entries

    def attach_block(self, qube: str, device: QubesDevice, read_only: bool = True) -> str:
        return f"dev:{device.bus_id} (peut-être monté comme {self.media_root / device.bus_id})"

    def detach_block(self, qube: str, device: QubesDevice) -> str:
        return f"dev detach {device.bus_id}"

    def wait_for_signal(self, timeout: float = 0.0) -> QubesDevice | None:
        d = self.list_devices()
        return d[0] if d else None