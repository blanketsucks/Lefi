import lefi
import pytest


@pytest.mark.asyncio
async def test_once() -> None:
    client = lefi.Client("token")

    @client.once("test_event")
    async def on_test_event() -> None:
        ...

    client._state.dispatch("test_event")
    assert client.once_events["test_event"] == []
