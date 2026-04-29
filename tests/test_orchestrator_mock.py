from pathlib import Path

from embedded_test_agent.config import load_config
from embedded_test_agent.models import TestContext
from embedded_test_agent.orchestrator import EmbeddedTestOrchestrator


def test_mock_orchestrator_generates_report(tmp_path):
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(str(root / "configs" / "demo.json"))
    ctx = TestContext(
        repo_path=str(root / "examples" / "firmware"),
        mock=True,
        output_dir=str(tmp_path / "report"),
        config=cfg,
        feishu_enabled=False,
    )
    result = EmbeddedTestOrchestrator().run(ctx)
    assert result.metrics["final_status"] == "FAIL"
    assert result.hypotheses
    assert Path(result.artifacts["report_md"]).exists()
    assert Path(result.artifacts["report_json"]).exists()
