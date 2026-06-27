import html
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Ensure project root is on sys.path when executed as a script.
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.email_service import send_nightbatch_summary_mail


SUBWORKFLOWS = [
    {
        "key": "fx",
        "name": "FX Update",
        "artifact_name": "nightbatch-fx-summary",
    },
    {
        "key": "eodhd",
        "name": "EODHD Import",
        "artifact_name": "nightbatch-eodhd-summary",
    },
    {
        "key": "tiingo",
        "name": "TIINGO Import",
        "artifact_name": "nightbatch-tiingo-summary",
    },
    {
        "key": "ishares",
        "name": "iShares Import",
        "artifact_name": "nightbatch-ishares-summary",
    },
]

DEFAULT_MAX_LOG_CHARS = 12000


def parse_admin_emails(raw_value: Any) -> List[str]:
    if raw_value is None:
        return []

    if isinstance(raw_value, (list, tuple)):
        return [str(item).strip() for item in raw_value if str(item).strip()]

    raw_text = str(raw_value).strip()
    if not raw_text:
        return []

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = [part.strip() for part in raw_text.split(",") if part.strip()]

    if not isinstance(parsed, list):
        raise ValueError("ADMIN_EMAILS must be a JSON array or comma-separated string")

    return [str(item).strip() for item in parsed if str(item).strip()]


def determine_overall_status(job_results: Dict[str, str]) -> str:
    ordered_statuses = [job_results.get(item["key"], "unknown") for item in SUBWORKFLOWS]
    if any(status in {"failure", "cancelled"} for status in ordered_statuses):
        return "failure"
    if any(status in {"skipped", "not_run_due_to_upstream_failure", "missing_artifact"} for status in ordered_statuses):
        return "partial"
    if all(status == "success" for status in ordered_statuses):
        return "success"
    return "unknown"


def _read_log(log_path: Path, max_chars: int) -> str:
    if not log_path.exists():
        return ""

    content = log_path.read_text(encoding="utf-8", errors="replace")
    if len(content) <= max_chars:
        return content

    truncated = len(content) - max_chars
    return (
        content[:max_chars]
        + "\n\n[truncated] "
        + f"{truncated} additional characters were omitted. See the workflow artifact for the full log."
    )


def load_subworkflow_sections(
    artifacts_root: Path,
    job_results: Dict[str, str],
    max_log_chars: int = DEFAULT_MAX_LOG_CHARS,
) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []

    for workflow in SUBWORKFLOWS:
        artifact_dir = artifacts_root / workflow["artifact_name"]
        metadata_path = artifact_dir / "metadata.json"
        fallback_status = job_results.get(workflow["key"], "unknown")

        if not metadata_path.exists():
            status = "not_run_due_to_upstream_failure" if fallback_status == "skipped" else "missing_artifact"
            sections.append(
                {
                    "key": workflow["key"],
                    "name": workflow["name"],
                    "status": status,
                    "start_time": None,
                    "finish_time": None,
                    "duration_seconds": None,
                    "output": "",
                }
            )
            continue

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        log_file = metadata.get("log_file", "script_output.log")
        output = _read_log(artifact_dir / log_file, max_chars=max_log_chars)

        sections.append(
            {
                "key": workflow["key"],
                "name": metadata.get("workflow_name", workflow["name"]),
                "status": metadata.get("status", fallback_status),
                "start_time": metadata.get("start_time"),
                "finish_time": metadata.get("finish_time"),
                "duration_seconds": metadata.get("duration_seconds"),
                "output": output,
            }
        )

    return sections


def build_subject(context: Dict[str, str], overall_status: str) -> str:
    repository = context.get("repository", "unknown-repository")
    ref_name = context.get("ref_name", "unknown-branch")
    run_number = context.get("run_number", "unknown")
    return f"Nightbatch Summary [{overall_status.upper()}] {repository} {ref_name} #{run_number}"


def render_text_summary(context: Dict[str, str], sections: Iterable[Dict[str, Any]], overall_status: str) -> str:
    lines = [
        "Nightbatch Summary",
        f"Repository: {context.get('repository', 'n/a')}",
        f"Branch: {context.get('ref_name', 'n/a')}",
        f"Run Number: {context.get('run_number', 'n/a')}",
        f"Overall Status: {overall_status}",
    ]

    run_url = context.get("run_url")
    if run_url:
        lines.append(f"Run URL: {run_url}")

    for section in sections:
        lines.extend(
            [
                "",
                f"=== {section['name']} ===",
                f"Status: {section.get('status', 'unknown')}",
                f"Start: {section.get('start_time') or 'n/a'}",
                f"Finish: {section.get('finish_time') or 'n/a'}",
                f"Duration (seconds): {section.get('duration_seconds') if section.get('duration_seconds') is not None else 'n/a'}",
                "Output:",
                section.get("output") or "No script output captured.",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def render_html_summary(context: Dict[str, str], sections: Iterable[Dict[str, Any]], overall_status: str) -> str:
    parts = [
        "<html><body>",
        "<h2>Nightbatch Summary</h2>",
        f"<p><strong>Repository:</strong> {html.escape(context.get('repository', 'n/a'))}<br>",
        f"<strong>Branch:</strong> {html.escape(context.get('ref_name', 'n/a'))}<br>",
        f"<strong>Run Number:</strong> {html.escape(context.get('run_number', 'n/a'))}<br>",
        f"<strong>Overall Status:</strong> {html.escape(overall_status)}</p>",
    ]

    run_url = context.get("run_url")
    if run_url:
        escaped_url = html.escape(run_url)
        parts.append(f'<p><strong>Run URL:</strong> <a href="{escaped_url}">{escaped_url}</a></p>')

    for section in sections:
        parts.extend(
            [
                f"<h3>{html.escape(section['name'])}</h3>",
                "<p>",
                f"<strong>Status:</strong> {html.escape(str(section.get('status', 'unknown')))}<br>",
                f"<strong>Start:</strong> {html.escape(str(section.get('start_time') or 'n/a'))}<br>",
                f"<strong>Finish:</strong> {html.escape(str(section.get('finish_time') or 'n/a'))}<br>",
                f"<strong>Duration (seconds):</strong> {html.escape(str(section.get('duration_seconds') if section.get('duration_seconds') is not None else 'n/a'))}",
                "</p>",
                f"<pre>{html.escape(section.get('output') or 'No script output captured.')}</pre>",
            ]
        )

    parts.append("</body></html>")
    return "".join(parts)


def send_summary_email_from_artifacts(
    artifacts_dir: str,
    admin_emails_raw: Any,
    job_results: Dict[str, str],
    context: Dict[str, str],
    max_log_chars: int = DEFAULT_MAX_LOG_CHARS,
) -> Dict[str, Any]:
    recipients = parse_admin_emails(admin_emails_raw)
    if not recipients:
        raise ValueError("ADMIN_EMAILS is empty; cannot send nightbatch summary")

    sections = load_subworkflow_sections(Path(artifacts_dir), job_results, max_log_chars=max_log_chars)
    overall_status = determine_overall_status({section["key"]: section["status"] for section in sections})
    subject = build_subject(context, overall_status)
    text_body = render_text_summary(context, sections, overall_status)
    html_body = render_html_summary(context, sections, overall_status)

    send_nightbatch_summary_mail(
        recipients=recipients,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )

    return {
        "recipients": recipients,
        "subject": subject,
        "overall_status": overall_status,
        "sections": sections,
    }


def _build_context_from_env() -> Dict[str, str]:
    repository = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")

    run_url = ""
    if repository and run_id:
        run_url = f"{server_url}/{repository}/actions/runs/{run_id}"

    return {
        "repository": repository,
        "ref_name": os.getenv("GITHUB_REF_NAME", ""),
        "run_number": os.getenv("GITHUB_RUN_NUMBER", ""),
        "run_url": run_url,
    }


def _build_job_results_from_env() -> Dict[str, str]:
    return {
        "fx": os.getenv("FX_JOB_RESULT", "unknown"),
        "eodhd": os.getenv("EODHD_JOB_RESULT", "unknown"),
        "tiingo": os.getenv("TIINGO_JOB_RESULT", "unknown"),
        "ishares": os.getenv("ISHARES_JOB_RESULT", "unknown"),
    }


def main() -> None:
    artifacts_dir = os.getenv("NIGHTBATCH_ARTIFACTS_DIR", "nightbatch-artifacts")
    admin_emails_raw = os.getenv("ADMIN_EMAILS", "")
    send_summary_email_from_artifacts(
        artifacts_dir=artifacts_dir,
        admin_emails_raw=admin_emails_raw,
        job_results=_build_job_results_from_env(),
        context=_build_context_from_env(),
    )


if __name__ == "__main__":
    main()