from __future__ import annotations

import re
import subprocess

from insecured.qubes.base import QubesBridge, QubesDevice


class QvmBridge(QubesBridge):
    """Vrai interfaçage sur un poste Qubes OS (sys-usb, dom0, qrexec)."""

    def __init__(self) -> None:
        self._cache: list[QubesDevice] = []

    def _qvm(self, *args: str) -> str:
        out = subprocess.run(["qvm-block", *args], capture_output=True, text=True)
        if out.returncode != 0:
            raise RuntimeError(out.stderr.strip() or "qvm-block failed")
        return out.stdout

    def list_devices(self) -> list[QubesDevice]:
        text = self._qvm("list")
        devices = []
        for line in text.splitlines()[1:]:
            m = re.match(r"^(\S+?):(\S+)\s+(.*)$", line)
            if m:
                devices.append(QubesDevice(bus_id=m.group(2), label=m.group(3).strip()))
        self._cache = devices
        return devices

    def attach_block(self, qube: str, device: QubesDevice, read_only: bool = True) -> str:
        self._qvm("attach", qube, f"sys-usb:{device.bus_id}")
        return f"{qube}:{device.bus_id}"

    def detach_block(self, qube: str, device: QubesDevice) -> str:
        self._qvm("detach", qube, f"sys-usb:{device.bus_id}")
        return f"detached {device.bus_id}"

    def wait_for_signal(self, timeout: float = 0.0) -> QubesDevice | None:
        raise NotImplementedError("signal udev: à implémenter via qrexec dans le qube app.")