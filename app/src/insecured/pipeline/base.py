from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

ProgressCallback = Callable[[str, int | None], None]


@dataclass
class StageContext:
    """Contexte partagé entre les étapes de la pipeline."""

    case: Any = None
    files: list = field(default_factory=list)
    data: dict = field(default_factory=dict)
    progress: ProgressCallback | None = None


class Stage(ABC):
    """Une étape modulaire de la pipeline d'analyse.

    Chaque stage reçoit un contexte, produit un résultat et peut mettre à jour
    le contexte (par exemple enrichir `files`). Les stages sont agnostiques de
    l'interface (GUI ou CLI) : ils ne font qu'appeler le callback de progrès.
    """

    name: str = "stage"

    @abstractmethod
    def run(self, ctx: StageContext) -> dict:
        """Exécute l'étape et retourne les données produites."""

    def _report(self, msg: str, progress: int | None = None) -> None:
        if self.cb:
            self.cb(msg, progress)

    @property
    def cb(self) -> ProgressCallback | None:
        return getattr(self, "_cb", None)

    def set_progress(self, cb: ProgressCallback | None) -> None:
        self._cb = cb