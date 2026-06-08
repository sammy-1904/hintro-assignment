"""Tests for meeting management endpoints."""

import pytest
from httpx import AsyncClient
from tests.conftest import register_and_login

SAMPLE_MEETING = {
    "title": "Sprint Planning",
    "participants": ["alice@example.com", "bob@example.com"],
    "meetingDate": "2026-05-20T10:00:00Z",
    "transcript": [
        {"timestamp": "00:10", "speaker": "John", "text": "We should launch next Friday."},
        {"timestamp": "00:20", "speaker": "Alice", "text": "I will prepare release notes."},
    ],
}


async def test_create_meeting(client: AsyncClient):
    token = await register_and_login(client)
    resp = await client.post(
        "/api/meetings",
        json=SAMPLE_MEETING,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Sprint Planning"
    assert "id" in body["data"]
    assert "traceId" in body


async def test_create_meeting_missing_title(client: AsyncClient):
    token = await register_and_login(client)
    payload = {**SAMPLE_MEETING, "title": ""}
    resp = await client.post(
        "/api/meetings", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_meeting_empty_transcript(client: AsyncClient):
    token = await register_and_login(client)
    payload = {**SAMPLE_MEETING, "transcript": []}
    resp = await client.post(
        "/api/meetings", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_get_meeting(client: AsyncClient):
    token = await register_and_login(client)
    create_resp = await client.post(
        "/api/meetings", json=SAMPLE_MEETING,
        headers={"Authorization": f"Bearer {token}"},
    )
    meeting_id = create_resp.json()["data"]["id"]

    resp = await client.get(
        f"/api/meetings/{meeting_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == meeting_id


async def test_get_meeting_not_found(client: AsyncClient):
    token = await register_and_login(client)
    resp = await client.get(
        "/api/meetings/nonexistent-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "MEETING_NOT_FOUND"


async def test_list_meetings_paginated(client: AsyncClient):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create 3 meetings
    for i in range(3):
        await client.post("/api/meetings", json={**SAMPLE_MEETING, "title": f"Meeting {i}"},
                          headers=headers)

    resp = await client.get("/api/meetings?page=1&per_page=2", headers=headers)
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["total"] == 3
    assert len(body["meetings"]) == 2
    assert body["page"] == 1


async def test_meeting_isolation_between_users(client: AsyncClient):
    """User A should not see User B's meetings."""
    # User A
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "password123"})
    token_a = (await client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})).json()["data"]["access_token"]
    await client.post("/api/meetings", json=SAMPLE_MEETING, headers={"Authorization": f"Bearer {token_a}"})

    # User B
    await client.post("/api/auth/register", json={"email": "b@example.com", "password": "password123"})
    token_b = (await client.post("/api/auth/login", json={"email": "b@example.com", "password": "password123"})).json()["data"]["access_token"]

    resp = await client.get("/api/meetings", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.json()["data"]["total"] == 0
