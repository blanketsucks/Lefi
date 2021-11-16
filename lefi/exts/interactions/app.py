from __future__ import annotations

from typing import Optional

from aiohttp import web

from lefi import InteractionType

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

__all__ = ("InteractionWeb",)


class InteractionWeb:
    def __init__(self, application_id: int, public_key: str) -> None:
        self.application_id = application_id
        self.verify_key = VerifyKey(bytes.fromhex(public_key))

        self.server = web.Application()
        self.server.add_routes([web.post("/", self.handle_interactions)])  # type: ignore

    async def validate_security(self, request: web.Request) -> bool:
        signature: Optional[str] = request.headers.get("X-Signature-Ed25519")
        timestamp: Optional[str] = request.headers.get("X-Signature-Timestamp")
        body = (await request.read()).decode("utf-8")

        if signature or timestamp is None:
            return False

        try:
            self.verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))  # type: ignore
            return True
        except BadSignatureError:
            return False

    async def handle_interactions(self, request: web.Request) -> web.Response:
        if not await self.validate_security(request):
            return web.Response(
                text="Could not verify request was from discord.", status=401
            )

        data = await request.json()
        interaction_type = InteractionType(data["type"])

        if interaction_type is InteractionType.PING:
            return web.json_response({"type": 1})

        return web.json_response({})

    async def start(self) -> None:
        ...
