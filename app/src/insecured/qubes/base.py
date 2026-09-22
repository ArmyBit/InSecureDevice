from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class QubesDevice:
    """Référence d'un bloc exposé par sys-usb (bus:device)."""

    bus_id: str
    label: str = ""
    dev_id: str = ""


class QubesBridge(ABC):
    """Port d'intégration Qubes.

    Cache les commandes Qubes (qvm-block, qrexec, udev) derrière une interface
    afin que l'application reste développable/testable hors d'un poste Qubes.
    """

    @abstractmethod
    def list_devices(self) -> list[QubesDevice]:
        ...

    @abstractmethod
    def attach_block(self, qube: str, device: QubesDevice, read_only: bool = True) -> str:
        ...

    @abstractmethod
    def detach_block(self, qube: str, device: QubesDevice) -> str:
        ...

    @abstractmethod
    def wait_for_signal(self, timeout: float = 0.0) -> QubesDevice | None:
        ...

    @property
    def available(self) -> bool:
        return True


def build_bridge(backend: str | None = None) -> QubesBridge:
    """Fabrique le bridge selon l'environnement.

    - "qvm": vrai interfaçage Qubes (qvm-block / qrexec).
    - "dev" par défaut: fallback de développement, sûr hors Qubes.
    """
    if backend == "qvm":
        from insecured.qubes.qvm import QvmBridge

        return QvmBridge()
    from insecured.qubes.dev import DevBridge

    return DevBridge()