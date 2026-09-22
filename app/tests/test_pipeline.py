import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from insecured.models.case import Case
from insecured.pipeline.base import StageContext
from insecured.pipeline.orchestrator import Orchestrator
from insecured.pipeline.stages import AnomalyStage, HashStage, InventoryStage, MetadataStage, VTStage
from insecured.pipeline.stages.vt_check import DevVTBackend, VirusTotalBackend
from insecured.pipeline.stages.ai_analysis import AIAnalysisStage, DevAIBackend


@pytest.fixture
def media(tmp_path: Path) -> Path:
    (tmp_path / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    (tmp_path / "fusil.pdf").write_bytes(b"%PDF-1.4\n% fake")
    (tmp_path / "double1.bin").write_bytes(b"A" * 100)
    (tmp_path / "double2.txt").write_bytes(b"A" * 100)
    (tmp_path / "empty.pdf").write_bytes(b"")
    return tmp_path


def _ctx(media: Path) -> StageContext:
    return StageContext(case=Case(name="t", image_path=media))


def test_orchestrator_runs_all_stages(media: Path):
    ctx = _ctx(media)
    orch = (
        Orchestrator()
        .add_stage(InventoryStage(mount_point=media))
        .add_stage(HashStage())
        .add_stage(MetadataStage())
        .add_stage(AnomalyStage())
    )
    results = orch.run(ctx)
    assert all(r.status == "ok" for r in results)
    assert len(ctx.files) == 5


def test_inventory_skips_hidden(media: Path):
    (media / ".hidden").write_bytes(b"x")
    ctx = _ctx(media)
    InventoryStage(mount_point=media).run(ctx)
    assert all(not f.path.name.startswith(".") for f in ctx.files)


def test_hash_matches_sha256(media: Path):
    ctx = _ctx(media)
    InventoryStage(mount_point=media).run(ctx)
    HashStage().run(ctx)
    expected = __import__("hashlib").sha256(b"A" * 100).hexdigest()
    by_name = {f.path.name: f for f in ctx.files}
    assert by_name["double1.bin"].sha256 == expected
    assert by_name["double1.bin"].sha256 == by_name["double2.txt"].sha256


def test_metadata_identifies_magic(media: Path):
    ctx = _ctx(media)
    InventoryStage(mount_point=media).run(ctx)
    MetadataStage().run(ctx)
    by_name = {f.path.name: f for f in ctx.files}
    assert "PNG" in by_name["photo.png"].magic
    assert "PDF" in by_name["fusil.pdf"].magic


def test_anomalies_detect_masked_duplicate(media: Path):
    ctx = _ctx(media)
    InventoryStage(mount_point=media).run(ctx)
    HashStage().run(ctx)
    MetadataStage().run(ctx)
    AnomalyStage().run(ctx)
    duplicated = [f for f in ctx.files if "doublon" in f.anom]
    assert len(duplicated) == 2


def test_ai_stage_survives_missing_backend(media: Path):
    ctx = _ctx(media)
    InventoryStage(mount_point=media).run(ctx)
    HashStage().run(ctx)
    MetadataStage().run(ctx)
    AnomalyStage().run(ctx)
    res = AIAnalysisStage(backend=DevAIBackend()).run(ctx)
    assert res["status"] == "ok"
    assert "DEV" in res["hits"][0]["notes"]


def test_ai_prompt_embeds_disassembly(media: Path):
    import struct

    exe = media / "malware.exe"
    d = bytearray(0x400)
    d[0:2] = b"MZ"
    struct.pack_into("<I", d, 0x3C, 0x80)
    d[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<H", d, 0x80 + 4, 0x14C)
    struct.pack_into("<H", d, 0x80 + 6, 1)
    struct.pack_into("<H", d, 0x80 + 20, 0xE0)
    opt = 0x80 + 24
    struct.pack_into("<H", d, opt, 0x10B)
    struct.pack_into("<I", d, opt + 16, 0x1000)
    struct.pack_into("<I", d, opt + 28, 0x00400000)
    sec = opt + 224
    code = bytes([0x55, 0x89, 0xE5, 0xB8, 0x2A, 0x00, 0x00, 0x00, 0x5D, 0xC3]) + b"\x90" * 16
    struct.pack_into("<I", d, sec + 8, len(code))
    struct.pack_into("<I", d, sec + 12, 0x1000)
    struct.pack_into("<I", d, sec + 16, len(code))
    struct.pack_into("<I", d, sec + 20, 0x200)
    d[0x200 : 0x200 + len(code)] = code
    exe.write_bytes(bytes(d))

    ctx = _ctx(media)
    InventoryStage(mount_point=media).run(ctx)
    HashStage().run(ctx)
    MetadataStage().run(ctx)
    AnomalyStage().run(ctx)

    captured = {}

    class CapturingAI:
        def analyze(self, prompt, max_tokens=None):
            captured["prompt"] = prompt
            return "[test]"

    exe_file = next(f for f in ctx.files if f.path.name == "malware.exe")
    exe_file.anom = "exécutable suspect générique"
    res = AIAnalysisStage(backend=CapturingAI()).run(ctx)
    assert res["status"] == "ok"
    assert captured["prompt"]
    assert "Extrait assembleur" in captured["prompt"]
    assert "push" in captured["prompt"]
    assert "0x2a" in captured["prompt"]
    assert all("asm_len" in h for h in res["hits"])


def test_vt_stage_dev_backend_marks_no_anomaly(media: Path):
    ctx = _ctx(media)
    InventoryStage(mount_point=media).run(ctx)
    HashStage().run(ctx)
    res = VTStage(backend=DevVTBackend()).run(ctx)
    assert res["status"] == "ok"
    assert all(not f.anom for f in ctx.files)
    assert len(res["hits"]) == len(ctx.files)


def test_vt_stage_flags_malicious_reputation():
    import hashlib

    from insecured.models.evidence import EvidenceFile

    class FakeVT:
        def check(self, sha256: str) -> dict:
            return {
                "found": True,
                "stats": {"malicious": 3, "suspicious": 1, "harmless": 0, "undetected": 68},
                "reputation": -12,
            }

    ctx = StageContext()
    f = EvidenceFile(path=__import__("pathlib").Path("evil.bin"), sha256=hashlib.sha256(b"x").hexdigest())
    ctx.files.append(f)
    res = VTStage(backend=FakeVT()).run(ctx)
    assert "VirusTotal" in f.anom
    assert res["hits"][0]["reputation"] == -12
    assert ctx.data["anomalies"] != []


def test_report_stage_generates_text_with_dev_ai(media: Path):
    from insecured.pipeline.stages.report import ReportStage

    class FakeAI:
        def analyze(self, prompt: str) -> str:
            return "RÉSUMÉ EXÉCUTIF\n[généré par IA test]"

    class FailingAI:
        def analyze(self, prompt: str) -> str:
            raise RuntimeError("connect")

    ctx = _ctx(media)
    InventoryStage(mount_point=media).run(ctx)
    HashStage().run(ctx)
    MetadataStage().run(ctx)
    AnomalyStage().run(ctx)

    res = ReportStage(backend=FakeAI()).run(ctx)
    assert res["status"] == "ok"
    assert "RÉSUMÉ EXÉCUTIF" in ctx.data["report_text"]

    ctx2 = _ctx(media)
    res2 = ReportStage(backend=FailingAI()).run(ctx2)
    assert res2["status"] == "ok"
    assert "RÉSUMÉ EXÉCUTIF" in ctx2.data["report_text"]  # fallback sans IA