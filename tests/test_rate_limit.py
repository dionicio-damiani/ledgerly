"""Unit tests for the in-memory rate limiter."""

from __future__ import annotations

import asyncio

import pytest

from app.rate_limit import InMemoryRateLimiter, parse_limit


def test_parse_limit_valid():
    assert parse_limit("30/minute") == (30, 60)
    assert parse_limit("5/second") == (5, 1)
    assert parse_limit("100/hour") == (100, 3600)


def test_parse_limit_invalid():
    with pytest.raises(ValueError):
        parse_limit("garbage")
    with pytest.raises(ValueError):
        parse_limit("5/year")


def test_limiter_allows_under_limit():
    rl = InMemoryRateLimiter("3/minute")

    async def run():
        return [await rl.hit("ip-1") for _ in range(3)]

    assert asyncio.run(run()) == [True, True, True]


def test_limiter_blocks_over_limit():
    rl = InMemoryRateLimiter("3/minute")

    async def run():
        for _ in range(3):
            await rl.hit("ip-1")
        return await rl.hit("ip-1")

    assert asyncio.run(run()) is False


def test_limiter_isolated_per_key():
    rl = InMemoryRateLimiter("2/minute")

    async def run():
        a = [await rl.hit("ip-A") for _ in range(2)]
        b = [await rl.hit("ip-B") for _ in range(2)]
        return a, b

    a, b = asyncio.run(run())
    assert a == [True, True]
    assert b == [True, True]


def test_limiter_returns_429_via_api(client, sample_payload, monkeypatch):
    from app.main import generate_limiter

    monkeypatch.setattr(generate_limiter, "limit", 2)
    generate_limiter.reset()

    assert client.post("/generate", json=sample_payload).status_code == 200
    assert client.post("/generate", json=sample_payload).status_code == 200
    blocked = client.post("/generate", json=sample_payload)
    assert blocked.status_code == 429
    assert blocked.json()["title"] == "Request failed"
