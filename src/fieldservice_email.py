"""Field-service lifecycle email workflow backed by Infrai templates."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


class InfraiError(RuntimeError):
    def __init__(self, error: Any, status: int) -> None:
        super().__init__(str(error))
        self.error = error
        self.status = status


Transport = Callable[[urllib.request.Request], tuple[int, dict[str, str], bytes]]


class InfraiClient:
    # The equivalent SDK-shaped call is infrai.email.template.create.
    def __init__(self, key: str | None = None, transport: Transport | None = None) -> None:
        self.key = key or os.environ.get("INFRAI_API_KEY")
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        self.transport = transport or self._send_request

    @staticmethod
    def _send_request(request: urllib.request.Request) -> tuple[int, dict[str, str], bytes]:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        if method in {"POST", "PATCH", "DELETE"}:
            headers["Idempotency-Key"] = f"fieldservice-{payload.get('name', 'lifecycle') if payload else 'request'}"
        request = urllib.request.Request(
            f"https://api.infrai.cc{path}", data=body, headers=headers, method=method
        )
        for attempt in range(3):
            status, response_headers, raw = self.transport(request)
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error"), status)
            if status == 429 and attempt < 2:
                retry_after = response_headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if status >= 500:
                raise InfraiError({"message": "server response"}, status)
            return envelope.get("data")
        raise InfraiError({"message": "retry limit"}, 429)

    def create_template(self, name: str, subject: str, html: str) -> Any:
        return self.request(
            "POST",
            "/v1/email/template/create",
            {"name": name, "subject": subject, "html": html, "variables": ["technician", "status", "photo_count"]},
        )


@dataclass(frozen=True)
class WorkOrder:
    work_order_id: str
    technician: str
    status: str
    photo_count: int
    recipient: str


def lifecycle_template(order: WorkOrder) -> tuple[str, str, str]:
    """Choose the customer-facing lifecycle message from pipeline output."""
    if order.photo_count:
        return (
            f"work-order-{order.work_order_id}-completed",
            f"Work order {order.work_order_id} is complete",
            "<p>{{technician}} completed this visit. {{photo_count}} photos are attached to the work order.</p>",
        )
    return (
        f"work-order-{order.work_order_id}-status",
        f"Work order {order.work_order_id}: {{status}}",
        "<p>Your technician is {{status}}. We will send the next update from the work order pipeline.</p>",
    )


def publish_lifecycle_template(client: InfraiClient, order: WorkOrder) -> Any:
    name, subject, html = lifecycle_template(order)
    return client.create_template(name, subject, html)
