import os
from typing import Iterable, List, Optional

import resend

try:
    import streamlit as st
except Exception:
    st = None


DEFAULT_FROM_EMAIL = "MiniPortfolioAnalysis <onboarding@resend.dev>"


def _read_streamlit_secret(key: str) -> Optional[str]:
    if st is None:
        return None
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def _get_resend_api_key() -> str:
    api_key = os.getenv("RESEND_KEY") or _read_streamlit_secret("RESEND_KEY")
    if not api_key:
        raise RuntimeError("Missing RESEND_KEY for email delivery")
    return api_key


def _get_from_email() -> str:
    return os.getenv("RESEND_FROM_EMAIL") or _read_streamlit_secret("RESEND_FROM_EMAIL") or DEFAULT_FROM_EMAIL


def _normalize_recipients(recipients: Iterable[str]) -> List[str]:
    normalized = []
    for recipient in recipients:
        if recipient is None:
            continue
        email = str(recipient).strip()
        if email:
            normalized.append(email)
    return normalized


def send_email_via_resend(
    recipients: Iterable[str],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
):
    normalized_recipients = _normalize_recipients(recipients)
    if not normalized_recipients:
        raise ValueError("At least one email recipient is required")

    resend.api_key = _get_resend_api_key()

    params = {
        "from": _get_from_email(),
        "to": normalized_recipients,
        "subject": subject,
        "html": html_body,
    }
    if text_body:
        params["text"] = text_body

    return resend.Emails.send(params)


def send_duplicate_info_mail(email):
    """
    Sends a notification email via Resend API if a user tries
    to register with an existing email address.
    """
    try:
        send_email_via_resend(
            recipients=[email],
            subject="Important: Registration Attempt",
            html_body=f"""
                <h3>Hello!</h3>
                <p>An attempt was made to register a new account with this email address (<strong>{email}</strong>).</p>
                <p>Since you already have an account with us, no new account was created.</p>
                <p>If this was you, you can simply log in as usual. If not, you can safely ignore this email.</p>
                <p>Best regards,<br>Your MiniPortfolioAnalysis Team</p>
            """,
        )
    except Exception as e:
        print(f"Error sending Resend email: {e}")


def send_nightbatch_summary_mail(
    recipients: Iterable[str],
    subject: str,
    text_body: str,
    html_body: str,
):
    return send_email_via_resend(
        recipients=recipients,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

  
