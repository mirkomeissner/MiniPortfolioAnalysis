import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from src.nightbatch.summary_email import load_subworkflow_sections, parse_admin_emails, send_summary_email_from_artifacts
from src.utils.email_service import send_nightbatch_summary_mail


def _write_artifact(root: Path, artifact_name: str, workflow_name: str, status: str, log_text: str) -> None:
    artifact_dir = root / artifact_name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "metadata.json").write_text(
        json.dumps(
            {
                "workflow_name": workflow_name,
                "status": status,
                "start_time": "2026-06-27T02:47:00Z",
                "finish_time": "2026-06-27T02:48:15Z",
                "duration_seconds": 75,
                "log_file": "script_output.log",
            }
        ),
        encoding="utf-8",
    )
    (artifact_dir / "script_output.log").write_text(log_text, encoding="utf-8")


def test_parse_admin_emails_accepts_json_array():
    assert parse_admin_emails('["admin1@example.com", " admin2@example.com "]') == [
        "admin1@example.com",
        "admin2@example.com",
    ]


def test_load_subworkflow_sections_handles_success_missing_and_skipped(tmp_path):
    _write_artifact(
        tmp_path,
        artifact_name="nightbatch-fx-summary",
        workflow_name="FX Update",
        status="success",
        log_text="line 1\nline 2\nline 3",
    )

    sections = load_subworkflow_sections(
        tmp_path,
        job_results={
            "fx": "success",
            "eodhd": "failure",
            "tiingo": "skipped",
            "ishares": "skipped",
        },
        max_log_chars=10,
    )

    assert sections[0]["name"] == "FX Update"
    assert sections[0]["status"] == "success"
    assert "[truncated]" in sections[0]["output"]

    assert sections[1]["status"] == "missing_artifact"
    assert sections[2]["status"] == "not_run_due_to_upstream_failure"
    assert sections[3]["status"] == "not_run_due_to_upstream_failure"


def test_send_summary_email_from_artifacts_builds_multi_section_mail(tmp_path):
    _write_artifact(
        tmp_path,
        artifact_name="nightbatch-fx-summary",
        workflow_name="FX Update",
        status="success",
        log_text="fx output",
    )

    with patch("src.nightbatch.summary_email.send_nightbatch_summary_mail") as mock_send:
        result = send_summary_email_from_artifacts(
            artifacts_dir=str(tmp_path),
            admin_emails_raw='["ops@example.com", "admin@example.com"]',
            job_results={
                "fx": "success",
                "eodhd": "skipped",
                "tiingo": "skipped",
                "ishares": "skipped",
            },
            context={
                "repository": "mirkomeissner/MiniPortfolioAnalysis",
                "ref_name": "dev",
                "run_number": "42",
                "run_url": "https://github.com/mirkomeissner/MiniPortfolioAnalysis/actions/runs/42",
            },
            max_log_chars=100,
        )

    assert result["recipients"] == ["ops@example.com", "admin@example.com"]
    assert result["overall_status"] == "partial"
    assert "Nightbatch Summary [PARTIAL]" in result["subject"]

    kwargs = mock_send.call_args.kwargs
    assert kwargs["recipients"] == ["ops@example.com", "admin@example.com"]
    assert "FX Update" in kwargs["text_body"]
    assert "fx output" in kwargs["text_body"]
    assert "not_run_due_to_upstream_failure" in kwargs["text_body"]


def test_send_nightbatch_summary_mail_uses_env_configuration(monkeypatch):
    monkeypatch.setenv("RESEND_KEY", "test-resend-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "MiniPortfolioAnalysis <batch@example.com>")

    with patch("src.utils.email_service.resend.Emails.send") as mock_send:
        send_nightbatch_summary_mail(
            recipients=["ops@example.com", "admin@example.com"],
            subject="Nightbatch test",
            text_body="plain text body",
            html_body="<p>html body</p>",
        )

    sent_payload = mock_send.call_args.args[0]
    assert sent_payload["to"] == ["ops@example.com", "admin@example.com"]
    assert sent_payload["from"] == "MiniPortfolioAnalysis <batch@example.com>"
    assert sent_payload["subject"] == "Nightbatch test"
    assert sent_payload["text"] == "plain text body"