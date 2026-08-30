"""Cross-platform event-loop tests for async PostgreSQL composition."""

import asyncio
import selectors
import sys

import pytest

from evalgate.entrypoints import retrieval_runtime


def test_database_event_loop_uses_select_selector_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[selectors.BaseSelector] = []
    original_factory = selectors.SelectSelector

    def capture_selector() -> selectors.BaseSelector:
        selector = original_factory()
        created.append(selector)
        return selector

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(selectors, "SelectSelector", capture_selector)

    loop = retrieval_runtime.database_event_loop()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
        assert len(created) == 1
    finally:
        loop.close()


def test_database_event_loop_uses_platform_default_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")

    loop = retrieval_runtime.database_event_loop()
    try:
        assert isinstance(loop, asyncio.AbstractEventLoop)
    finally:
        loop.close()
