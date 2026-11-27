import json

from src.fieldservice_email import InfraiClient, WorkOrder, lifecycle_template


def test_photos_select_completion_template():
    order = WorkOrder("WO-7", "Ravi", "completed", 3, "customer@example.com")

    name, subject, html = lifecycle_template(order)

    assert name == "work-order-WO-7-completed"
    assert subject == "Work order WO-7 is complete"
    assert "{{photo_count}}" in html


def test_template_request_uses_server_template_variables():
    captured = []

    def transport(request):
        captured.append((request.method, request.full_url, json.loads(request.data)))
        return 200, {}, b'{"ok": true, "data": {"id": "tpl-1"}}'

    client = InfraiClient(key="test-key", transport=transport)
    client.create_template("work-order-WO-7-status", "Work order WO-7: scheduled", "<p>{{status}}</p>")

    method, url, payload = captured[0]
    assert method == "POST"
    assert url.endswith("/v1/email/template/create")
    assert payload["variables"] == ["technician", "status", "photo_count"]
