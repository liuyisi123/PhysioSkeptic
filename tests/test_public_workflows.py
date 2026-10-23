"""Regression checks for the public offline examples and source archive."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pytest
import yaml
from jsonschema import ValidationError

from physioskeptic.debate import PhysioSkepticDebate
from physioskeptic.llm_clients import MockLLMClient
from physioskeptic.metrics import macro_f1, expected_calibration_error, multiclass_brier, nll
from physioskeptic.patch_report import validate_patch_report

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return json.loads((ROOT / "data/sample_patch_report.json").read_text(encoding="utf-8"))


class FastClient(MockLLMClient):
    def complete_json(self, role, system, user, schema=None):
        response = super().complete_json(role, system, user, schema)
        if role == "Proposer":
            response["confidence"] = 0.95
        if role == "Checker":
            response.update(severity="NONE", conflicts=[])
        return response


def test_fast_transcript_keeps_checker():
    report = sample()
    report["q_hat"] = 0.95
    result = PhysioSkepticDebate(FastClient(), ROOT / "prompts").run(report)
    assert result.route.value == "FAST"
    assert [turn["role"] for turn in result.transcript] == ["Proposer", "Checker", "Arbiter"]


def test_low_quality_has_three_challenges_and_formatted_system():
    class InspectClient(MockLLMClient):
        def complete_json(self, role, system, user, schema=None):
            assert "{n_chal}" not in system
            return super().complete_json(role, system, user, schema)

    report = sample()
    report["q_hat"] = 0.2
    result = PhysioSkepticDebate(InspectClient(), ROOT / "prompts").run(report)
    skeptic = next(turn for turn in result.transcript if turn["role"] == "Skeptic")
    assert len(skeptic["challenges"]) == 3


def test_invalid_role_output_is_rejected():
    class InvalidClient(MockLLMClient):
        def complete_json(self, *args, **kwargs):
            return {"role": "Proposer", "confidence": 2}

    with pytest.raises(ValidationError):
        PhysioSkepticDebate(InvalidClient(), ROOT / "prompts").run(sample())


def test_nonfinite_report_is_rejected():
    report = sample()
    report["hr_ecg"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        validate_patch_report(report, ROOT / "data/patch_report.schema.json")


def test_macro_f1_includes_all_five_classes():
    assert macro_f1(["SR"], ["SR"]) == pytest.approx(0.2)


def test_ece_includes_zero_confidence():
    assert expected_calibration_error(np.array([0.0]), np.array([1.0])) == 1.0


@pytest.mark.parametrize("prob", [np.array([[-0.2, 1.2]]), np.array([[np.nan, 1.0]])])
def test_invalid_probabilities_are_rejected(prob):
    with pytest.raises(ValueError):
        multiclass_brier(np.array([0]), prob)


def test_nll_retains_missing_classes():
    assert nll(np.array([0]), np.array([[0.5, 0.25, 0.25]])) == pytest.approx(-np.log(0.5))


def test_json_report_cli_reads_custom_config(tmp_path):
    config = yaml.safe_load((ROOT / "configs/default.yaml").read_text(encoding="utf-8"))
    config["routing"]["review_confidence"] = 0.99
    config_path = tmp_path / "custom.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    out = tmp_path / "predictions.jsonl"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_eval.py"),
            "--config",
            str(config_path),
            "--input",
            str(ROOT / "data/sample_patch_report.json"),
            "--output",
            str(out),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    assert json.loads(out.read_text(encoding="utf-8"))["final"]["review_recommended"] is True


def test_source_packager_excludes_private_files(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "release_packager", ROOT / "scripts/make_release_zip.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [
        ".git/config",
        "outputs/private.jsonl",
        "src/__pycache__/x.pyc",
        "src/secrets.key",
        "data/raw/record.json",
        "src/.env",
    ]:
        assert not module.public_path(name)
    assert module.public_path("src/physioskeptic/debate.py")
    assert module.public_path("data/sample_patch_report.json")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("Synthetic packaging fixture", encoding="utf-8")
    (tmp_path / ".env").write_text("SYNTHETIC_ONLY=1", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", ".env"], cwd=tmp_path, check=True)
    target = tmp_path / "source.zip"
    module.create_archive(target, root=tmp_path)
    with zipfile.ZipFile(target) as archive:
        assert archive.namelist() == ["PhysioSkeptic/README.md"]
    with pytest.raises(FileExistsError):
        module.create_archive(target, root=tmp_path)
