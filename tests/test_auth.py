"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "alice@example.com",
        "password": "securepassword1",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["user"]["email"] == "alice@example.com"
    assert "traceId" in body


async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "alice@example.com", "password": "securepassword1"}
    await client.post("/api/auth/register", json=payload)
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_TAKEN"


async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "securepassword1",
    })
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "short",
    })
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "bob@example.com",
        "password": "bobspassword1",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "bob@example.com",
        "password": "bobspassword1",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["access_token"] is not None


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "carol@example.com",
        "password": "rightpassword1",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "carol@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "doesntmatter",
    })
    assert resp.status_code == 401
    # Same error message — should not reveal whether email exists
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_protected_route_without_token(client: AsyncClient):
    resp = await client.get("/api/meetings")
    assert resp.status_code == 401


async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "UP"
