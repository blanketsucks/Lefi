from __future__ import annotations

import struct
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from enum import IntEnum
import aiohttp
import asyncio

if TYPE_CHECKING:
    from .protocol import VoiceClient

__all__ = ("OpCodes", "VoiceWebSocketClient")


class OpCodes(IntEnum):
    IDENTIFY = 0
    SELECT_PROTOCOL = 1
    READY = 2
    HEARTBEAT = 3
    SESSION_DESCRIPTION = 4
    SPEAKING = 5
    HEARTBEAT_ACK = 6
    RESUME = 7
    HELLO = 8
    RESUMED = 9
    CLIENT_CONNECT = 12
    CLIENT_DISCONNECT = 13


class SpeakingState(IntEnum):
    NONE = 0
    VOICE = 1
    SOUNDSHARE = 2
    PRIORITY = 4


class VoiceWebSocketClient:
    def __init__(self, client: VoiceClient, guild_id: int, user_id: int) -> None:
        self.client = client
        self.guild_id = guild_id
        self.user_id = user_id

        self.ws: aiohttp.ClientWebSocketResponse = None  # type: ignore
        self.secret_key: List[int] = []
        self.ssrc: Optional[int] = None
        self.mode: Optional[str] = None
        self.remote_ip: str = ""
        self.remote_port: int = 0
        self.closed = False

        self._heartbeat_handler: Optional[asyncio.Task] = None
        self._reader_handler: Optional[asyncio.Task] = None

    @property
    def remote_addr(self) -> Tuple[str, int]:
        return self.remote_ip, self.remote_port

    async def start_heartbeat(self, interval: float):
        while not self.closed:
            payload = {"op": OpCodes.HEARTBEAT, "d": (time.time() * 1000)}

            await self.ws.send_json(payload)
            await asyncio.sleep(interval)

    async def connect(self):
        state = self.client._state
        url = f"wss://{self.client.endpoint}/?v=4"

        self.ws = await state.http.ws_connect(url)
        await self.identify()

        while not self.secret_key:
            await self.receive()

        self._reader_handler = self.client.loop.create_task(self.read_messages())

    async def close(self):
        if self._reader_handler:
            self._reader_handler.cancel()

        if self._heartbeat_handler:
            self._heartbeat_handler.cancel()

        await self.ws.close()
        self.closed = True

    async def identify(self):
        payload = {
            "op": OpCodes.IDENTIFY,
            "d": {
                "server_id": str(self.guild_id),
                "user_id": str(self.user_id),
                "session_id": self.client.session_id,
                "token": self.client.token,
            },
        }

        await self.ws.send_json(payload)

    async def receive(self):
        message = await self.ws.receive()
        if message.type in (
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.CLOSING,
            aiohttp.WSMsgType.CLOSE,
        ):
            await self.ws.close()
            return

        data = message.json()
        payload = data["d"]

        if data["op"] == OpCodes.READY:
            await self.ready(data)

        elif data["op"] == OpCodes.SESSION_DESCRIPTION:
            self.mode = payload["mode"]
            self.secret_key = payload["secret_key"]

        elif data["op"] == OpCodes.HELLO:
            interval = payload["heartbeat_interval"] / 1000
            self._heartbeat_handler = self.client.loop.create_task(
                self.start_heartbeat(interval)
            )

    async def read_messages(self):
        while not self.closed:
            await self.receive()

    async def ready(self, data: Dict):
        payload = data["d"]

        self.ssrc = payload["ssrc"]
        self.remote_ip = payload["ip"]
        self.remote_port = payload["port"]

        await self.udp_connect()

        mode = self.select_mode(payload["modes"])
        await self._perform_ip_discovery(mode)

    def select_mode(self, modes: List[str]):
        supported = self.client.protocol.supported_modes.keys()
        return [mode for mode in modes if mode in supported][0]

    async def udp_connect(self):
        await self.client.loop.create_datagram_endpoint(
            self.client.protocol, remote_addr=self.remote_addr
        )

    async def _perform_ip_discovery(self, mode: str):
        packet = bytearray(70)

        struct.pack_into(">H", packet, 0, 0x1)
        struct.pack_into(">H", packet, 2, 70)
        struct.pack_into(">I", packet, 4, self.ssrc)

        await self.client.protocol.sendto(packet, self.remote_addr)
        data = await self.client.protocol.read()

        start = 4
        end = data.index(b"\x00", start)

        ip = data[start:end].decode("ascii")
        port = struct.unpack_from(">H", data, len(data) - 2)[0]

        await self.select_protocol(ip, port, mode)

    async def select_protocol(self, ip: str, port: int, mode: str):
        payload = {
            "op": OpCodes.SELECT_PROTOCOL,
            "d": {
                "protocol": "udp",
                "data": {"address": ip, "port": port, "mode": mode},
            },
        }

        await self.ws.send_json(payload)

    async def speak(self, state: SpeakingState):
        payload = {
            "op": OpCodes.SPEAKING,
            "d": {
                "speaking": state.value,
                "delay": 0,
            },
        }

        await self.ws.send_json(payload)
