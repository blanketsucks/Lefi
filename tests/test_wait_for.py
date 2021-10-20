import asyncio

import pytest

import lefi


class FakeMessage:
    def __init__(self, id, author_id):
        self.id = id
        self.author_id = author_id


@pytest.mark.asyncio
async def test_wait_for() -> None:
    class FakeClient(lefi.Client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.message: FakeMessage = None  # type: ignore

    client = FakeClient("token")

    @client.on("test_event")
    async def on_test_event(client) -> None:
        message = await client.wait_for("message_create", check=lambda msg: msg.id == 2)

        client.message = message

    client._state.dispatch("test_event", client)
    await asyncio.sleep(3)

    client._state.dispatch("message_create", FakeMessage(2, 2))
    await asyncio.sleep(3)

    assert client.message.id == 2 and client.message.author_id == 2
