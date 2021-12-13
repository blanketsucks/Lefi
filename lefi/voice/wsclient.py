from __future__ import annotations

import struct
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union
from enum import IntEnum
import aiohttp
import asyncio

from .protocol import UNSIGNED_INT, UNSIGNED_SHORT

if TYPE_CHECKING:
    from ..state import State
    from .client import VoiceClient

__all__ = ("OpCodes", "VoiceWebSocketClient", "UserVoiceData")


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


class UserVoiceData:
    def __init__(self, state: State, ssrc: int, user_id: int) -> None:
        self.ssrc = ssrc
        self.user_id = user_id
        self.user = state.get_user(user_id)

    def __repr__(self) -> str:
        return f"<UserVoiceData ssrc={self.ssrc} user_id={self.user_id} user={self.user}>"


class VoiceWebSocketClient:
    def __init__(self, client: VoiceClient, guild_id: int, user_id: int) -> None:
        self.client = client
        self.guild_id = guild_id
        self.state = client._state
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

        self._ssrc_to_user_data: Dict[int, UserVoiceData] = {}
        self._user_id_to_ssrc: Dict[int, int] = {}

    def add_user(self, ssrc: int, user_id: int) -> UserVoiceData:
        data = UserVoiceData(self.state, ssrc, user_id)

        self._ssrc_to_user_data[ssrc] = data
        self._user_id_to_ssrc[user_id] = ssrc

        return data

    def remove_user(self, user_id: int) -> Optional[UserVoiceData]:
        ssrc = self._user_id_to_ssrc.pop(user_id, None)
        if ssrc is not None:
            return self._ssrc_to_user_data.pop(ssrc)

        return None

    def get_user(self, ssrc: int) -> Optional[UserVoiceData]:
        return self._ssrc_to_user_data.get(ssrc)

    @property
    def remote_addr(self) -> Tuple[str, int]:
        return self.remote_ip, self.remote_port

    async def start_heartbeat(self, interval: float) -> None:
        while not self.closed:
            payload = {"op": OpCodes.HEARTBEAT, "d": (time.time() * 1000)}

            await self.ws.send_json(payload)
            await asyncio.sleep(interval)

    async def connect(self) -> None:
        state = self.client._state
        url = f"wss://{self.client.endpoint}/?v=4"

        self.ws = await state.http.ws_connect(url)
        await self.identify()

        while not self.secret_key:
            await self.receive()

        self._reader_handler = self.client.loop.create_task(self.read_messages())

    async def close(self) -> None:
        if self._reader_handler:
            self._reader_handler.cancel()

        if self._heartbeat_handler:
            self._heartbeat_handler.cancel()

        await self.ws.close()
        self.closed = True

    async def receive(self) -> None:
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
            self._heartbeat_handler = self.client.loop.create_task(self.start_heartbeat(interval))

        elif data["op"] == OpCodes.SPEAKING:
            user_id = int(payload["user_id"])
            ssrc = payload["ssrc"]

            data = self.add_user(ssrc, user_id)
            self.state.dispatch("speaking_update", data, bool(payload["speaking"]))

        elif data["op"] == OpCodes.CLIENT_CONNECT:
            data = self.add_user(payload["audio_ssrc"], int(data["user_id"]))
            self.state.dispatch("client_connect", data)

        elif data["op"] == OpCodes.CLIENT_DISCONNECT:
            data = self.remove_user(int(data["user_id"]))
            if data:
                self.state.dispatch("client_disconnect", data)

    async def read_messages(self) -> None:
        while not self.closed:
            await self.receive()

    async def ready(self, data: Dict) -> None:
        payload = data["d"]

        self.ssrc = payload["ssrc"]
        self.remote_ip = payload["ip"]
        self.remote_port = payload["port"]

        await self.udp_connect()

        mode = self.select_mode(payload["modes"])
        await self._perform_ip_discovery(mode)

    def select_mode(self, modes: List[str]) -> str:
        supported = self.client.protocol.SUPPORTED_MODES
        return [mode for mode in modes if mode in supported][0]

    async def udp_connect(self) -> None:
        await self.client.loop.create_datagram_endpoint(self.client.protocol, remote_addr=self.remote_addr)

    async def _perform_ip_discovery(self, mode: str) -> None:
        packet = bytearray(70)

        UNSIGNED_SHORT.pack_into(packet, 0, 0x1)
        UNSIGNED_SHORT.pack_into(packet, 2, 70)
        UNSIGNED_INT.pack_into(packet, 4, self.ssrc)

        await self.client.protocol.write(packet)
        data = await self.client.protocol.read()

        start = 4
        end = data.index(b"\x00", start)

        ip = data[start:end].decode("ascii")
        port = struct.unpack_from(">H", data, len(data) - 2)[0]

        await self.select_protocol(ip, port, mode)

    async def identify(self) -> None:
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

    async def select_protocol(self, ip: str, port: int, mode: str) -> None:
        payload = {
            "op": OpCodes.SELECT_PROTOCOL,
            "d": {
                "protocol": "udp",
                "data": {"address": ip, "port": port, "mode": mode},
            },
        }

        await self.ws.send_json(payload)

    async def speak(self, state: SpeakingState) -> None:
        payload = {
            "op": OpCodes.SPEAKING,
            "d": {
                "speaking": state.value,
                "delay": 0,
            },
        }

        await self.ws.send_json(payload)
