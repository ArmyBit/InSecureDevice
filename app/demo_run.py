import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from insecured.models.case import Case
from insecured.pipeline.base import StageContext
from insecured.pipeline.orchestrator import Orchestrator
from insecured.pipeline.stages import (
    AnomalyStage,
    AIAnalysisStage,
    DevVTBackend,
    HashStage,
    InventoryStage,
    MetadataStage,
    VTStage,
)
from insecured.pipeline.stages.ai_analysis import build_ai_backend

demo = Path("DEV_MEDIA")
demo.mkdir(exist_ok=True)
(demo / "rapport.pdf").write_bytes(b"%PDF-1.4\nfake pdf content")
(demo / "stegano.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 128)
(demo / "photo.bin").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)  # PNG masqué en .bin
(demo / "clean.txt").write_bytes(b"nothing suspicious")
(demo / "dupA.exe").write_bytes(b"MZ\x90\x00" + b"X" * 100)
(demo / "dupB.dll").write_bytes(b"MZ\x90\x00" + b"X" * 100)  # doublon masqué

ctx = StageContext(case=Case(name="demo", image_path=demo, operator="CI"))
orch = (
    Orchestrator()
    .add_stage(InventoryStage(mount_point=demo))
    .add_stage(HashStage())
    .add_stage(MetadataStage())
    .add_stage(AnomalyStage())
    .add_stage(VTStage(backend=DevVTBackend()))
    .add_stage(AIAnalysisStage(backend=build_ai_backend()))
)
for r in orch.run(ctx):
    print(f"[{r.stage:>10}] {r.status:<6} {r.message}")

print("\n--- Fichiers avec anomalie ---")
for f in ctx.files:
    if f.anom:
        print(f"  {f.path.name:14} {f.magic:24} anomaly={f.anom} notes={f.notes[:40]}")
print(f"\nTotal: {len(ctx.files)} fichiers, anomalies=", ctx.data.get('anomalies', []))