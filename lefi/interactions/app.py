from __future__ import annotations

import typing

from aiohttp import web

import enum

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError


class InteractionType(enum.IntEnum):
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3


class App(web.Application):
    def __init__(self, client, pub_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_routes([web.post("/", self.process_interactions)])  # type: ignore
        self._commands: typing.Dict[str, typing.Coroutine] = {}
        self.pub_key = pub_key
        self.client = client

    async def security_check(self, request: web.Request) -> bool:
        verify_key = VerifyKey(bytes.fromhex(self.pub_key))

        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")
        body = (await request.read()).decode("utf-8")

        if signature:
            try:
                verify_key.verify(
                    f"{timestamp}{body}".encode(), bytes.fromhex(signature)
                )
                return True
            except BadSignatureError:
                return False
        else:
            return False

    async def register_commands(self) -> None:
        raise NotImplementedError

    async def process_interactions(self, request: web.Request):
        if not await self.security_check(request):
            return web.Response(text="invalid request signature", status=401)

        data = await request.json()

        if data["type"] == InteractionType.PING:
            return {"type": 1}

        elif data["type"] == InteractionType.APPLICATION_COMMAND:
            return web.json_response({})  # TODO: fully impl after more models

    async def startup(self) -> None:
        ...  # register commands here

    async def run(self) -> None:
        self.runner = web.AppRunner(self)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner)
        await self.site.start()
