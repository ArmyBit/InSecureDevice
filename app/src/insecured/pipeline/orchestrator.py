from __future__ import annotations

from pathlib import Path

from insecured.models.case import Case
from insecured.models.report import PipelineResult
from insecured.pipeline.base import Stage, StageContext


class Orchestrator:
    """Pilote l'exécution séquentielle des stages de la pipeline."""

    def __init__(self) -> None:
        self.stages: list[Stage] = []
        self.results: list[PipelineResult] = []
        self.on_stage_start = lambda stage: None
        self.on_stage_end = lambda stage, result: None

    def add_stage(self, stage: Stage) -> "Orchestrator":
        self.stages.append(stage)
        return self

    def run(self, ctx: StageContext, case: Case | None = None) -> list[PipelineResult]:
        self.results = []
        if case is not None:
            ctx.case = case
        for stage in self.stages:
            stage.set_progress(ctx.progress)
            self.on_stage_start(stage.name)
            try:
                data = stage.run(ctx)
                data.pop("status", "ok")
                result = PipelineResult(stage=stage.name, status="ok", data=data)
            except Exception as exc:
                data = {}
                result = PipelineResult(stage=stage.name, status="error", message=str(exc))
            self.results.append(result)
            self.on_stage_end(stage.name, result)
            if result.status == "error":
                break
        return self.results

    def summary(self) -> list[dict]:
        return [r.to_dict() for r in self.results]