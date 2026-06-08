"""Tests for action item management endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from tests.conftest import register_and_login

FUTURE_DATE = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
PAST_DATE = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

SAMPLE_ITEM = {
    "task": "Prepare release notes",
    "assignee": "alice@example.com",
    "dueDate": FUTURE_DATE,
    "citations": [{"timestamp": "00:20"}],
}


async def test_create_action_item(client: AsyncClient):
    token = await register_and_login(client)
    resp = await client.post(
        "/api/action-items",
        json=SAMPLE_ITEM,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["task"] == "Prepare release notes"
    assert body["data"]["status"] == "PENDING"
    assert body["data"]["citations"] == [{"timestamp": "00:20"}]


async def test_create_action_item_missing_fields(client: AsyncClient):
    token = await register_and_login(client)
    resp = await client.post(
        "/api/action-items",
        json={"task": "Something"},  # missing assignee and dueDate
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_update_status(client: AsyncClient):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/api/action-items", json=SAMPLE_ITEM, headers=headers)
    item_id = create_resp.json()["data"]["id"]

    resp = await client.patch(
        f"/api/action-items/{item_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "IN_PROGRESS"


async def test_update_invalid_status(client: AsyncClient):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/api/action-items", json=SAMPLE_ITEM, headers=headers)
    item_id = create_resp.json()["data"]["id"]

    resp = await client.patch(
        f"/api/action-items/{item_id}/status",
        json={"status": "INVALID_STATUS"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_list_action_items_filter_by_status(client: AsyncClient):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/action-items", json=SAMPLE_ITEM, headers=headers)
    await client.post("/api/action-items", json={**SAMPLE_ITEM, "task": "Task 2"}, headers=headers)

    resp = await client.get("/api/action-items?status=PENDING", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert all(i["status"] == "PENDING" for i in items)


async def test_overdue_items(client: AsyncClient):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create one future item (not overdue)
    await client.post("/api/action-items", json=SAMPLE_ITEM, headers=headers)

    # Create one past item (overdue)
    await client.post("/api/action-items", json={**SAMPLE_ITEM, "dueDate": PAST_DATE}, headers=headers)

    resp = await client.get("/api/action-items/overdue", headers=headers)
    assert resp.status_code == 200
    overdue = resp.json()["data"]
    assert len(overdue) == 1
    assert overdue[0]["task"] == "Prepare release notes"


async def test_completed_items_not_overdue(client: AsyncClient):
    """Completed items should not appear in overdue list even if past due."""
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/action-items",
        json={**SAMPLE_ITEM, "dueDate": PAST_DATE},
        headers=headers,
    )
    item_id = create_resp.json()["data"]["id"]

    # Mark as completed
    await client.patch(f"/api/action-items/{item_id}/status", json={"status": "COMPLETED"}, headers=headers)

    resp = await client.get("/api/action-items/overdue", headers=headers)
    assert len(resp.json()["data"]) == 0
