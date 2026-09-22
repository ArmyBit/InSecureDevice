from dataclasses import dataclass, field
from datetime import datetime, timezone

from insecured.models.case import Case
from insecured.models.evidence import EvidenceFile
from insecured.models.report import PipelineResult


@dataclass
class CaseSession:
    """Une analyse (opération) complète, affichée comme une carte du dashboard."""

    case: Case
    mount_point: str = ""
    status: str = "running"  # running | done | error
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    files: list[EvidenceFile] = field(default_factory=list)
    results: list[PipelineResult] = field(default_factory=list)
    stages: dict[str, str] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    anomalies: int = 0
    report_text: str = ""

    @property
    def counts(self) -> tuple[int, int, int]:
        """(total, sains, suspects)."""
        total = len(self.files)
        suspects = sum(1 for f in self.files if f.is_suspicious)
        return total, total - suspects, suspects

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    def finalize(self, ctx_files: list[EvidenceFile], results: list[PipelineResult], anomalies: int) -> None:
        self.files = ctx_files
        self.results = results
        self.anomalies = anomalies
        self.finished_at = datetime.now(timezone.utc)
        self.status = "error" if any(r.status == "error" for r in results) else "done"