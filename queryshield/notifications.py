"""Notification helpers — Discord webhook + SendGrid email.

Used for ops alerts (process boot, repeated safety blocks, quota alerts).
Both helpers are best-effort: a missing webhook URL or API key turns them
into no-ops rather than raising.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from queryshield.config import get_settings

log = logging.getLogger("queryshield.notifications")


def discord_alert(title: str, body: str, severity: str = "info") -> None:
    settings = get_settings()
    url = settings.discord_webhook_url
    if not url:
        return
    color = {"info": 0x3498DB, "warn": 0xF1C40F, "error": 0xE74C3C}.get(severity, 0x3498DB)
    payload = {
        "embeds": [
            {
                "title": f"[QueryShield · {settings.env}] {title}",
                "description": body[:1900],
                "color": color,
            }
        ]
    }
    try:
        httpx.post(url, json=payload, timeout=5.0)
    except Exception as e:  # noqa: BLE001
        log.warning("discord_alert failed: %s", e)


def send_email(to: str, subject: str, body: str, html: Optional[str] = None) -> bool:
    settings = get_settings()
    if not settings.sendgrid_api_key:
        log.info("send_email noop (no SENDGRID_API_KEY): %s -> %s", subject, to)
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        msg = Mail(
            from_email=settings.sendgrid_from,
            to_emails=to,
            subject=subject,
            plain_text_content=body,
            html_content=html or body.replace("\n", "<br>"),
        )
        client = SendGridAPIClient(settings.sendgrid_api_key)
        response = client.send(msg)
        return 200 <= response.status_code < 300
    except Exception as e:  # noqa: BLE001
        log.warning("send_email failed: %s", e)
        return False
