from __future__ import annotations

import asyncio
import contextlib
from typing import List, cast

import pytest
from channels.auth import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.test import override_settings

from rest_framework_simplejwt.tokens import RefreshToken

from shuttle.demultiplexer import Demultiplexer
from shuttle.utils.jwt_auth import JWTAuthMiddlewareStack

INMEM_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@pytest.fixture(scope="session", autouse=True)
def channels_inmemory_layer():
    with override_settings(CHANNEL_LAYERS=INMEM_LAYERS):
        yield


@pytest.fixture(scope="session", autouse=True)
def load_yaml_fixtures(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command(
            "loaddata",
            "tenant_profile.yaml",
            "tenant.yaml",
            "roles_permissions.yaml",
            "users.yaml",
            "room.yaml",
            verbosity=0,
        )


@pytest.fixture
@database_sync_to_async
def karina_token():
    user = authenticate(email="karina@gmail.com", password="password")
    if not user:
        return ""

    refresh = cast(RefreshToken, RefreshToken.for_user(user))
    return refresh.access_token


@pytest.fixture
def asgi_app() -> object:
    return JWTAuthMiddlewareStack(Demultiplexer.as_asgi())


@pytest.fixture
async def ws_connect(asgi_app):
    """
    Connection factory: you transfer a token, you get a connected communicator.
    Automatically terminate all created connections after the test.
    """
    opened: List[WebsocketCommunicator] = []

    async def _connect(token: str) -> WebsocketCommunicator:
        comm = WebsocketCommunicator(asgi_app, f"/api/ws/v2/?token={token}")
        connected, _ = await comm.connect()
        assert connected, "WebSocket должен подключаться"
        opened.append(comm)
        return comm

    try:
        yield _connect
    finally:
        for comm in opened[::-1]:
            future = getattr(comm, "future", None)
            if future is not None and future.done():
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    future.result()
            else:
                with contextlib.suppress(asyncio.CancelledError):
                    await comm.disconnect()
            await asyncio.sleep(0)
