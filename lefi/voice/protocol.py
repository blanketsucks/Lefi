from __future__ import annotations

import contextlib
import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)
import struct

try:
    import nacl.secret
except ImportError:
    has_nacl = False
else:
    has_nacl = True

from .ws import VoiceWebSocketClient

if TYPE_CHECKING:
    from ..state import State
    from ..objects import VoiceChannel

    Encrypter = Callable[[bytes, bytes], bytes]

__all__ = (
    "VoiceProtocol",
    "VoiceClient",
)


class VoiceProtocol(asyncio.streams.FlowControlMixin, asyncio.DatagramProtocol):
    if TYPE_CHECKING:
        _loop: asyncio.AbstractEventLoop
        _paused: bool

        async def _drain_helper(self):
            ...

    def __init__(self, client: VoiceClient):
        self.client = client
        self.queue = asyncio.Queue[bytes]()

        self.timestamp = 0
        self.sequence = 0
        self.lite_nonce = 0

        self.supported_modes: Dict[str, Encrypter] = {
            "xsalsa20_poly1305": self.encrypt_xsalsa20_poly1305,
            "xsalsa20_poly1305_suffix": self.encrypt_xsalsa20_poly1305_suffix,
            "xsalsa20_poly1305_lite": self.encrypt_xsalsa20_poly1305_lite,
        }

        self._secret_box: Optional[nacl.secret.SecretBox] = None
        super().__init__()

    @property
    def ssrc(self) -> Optional[str]:
        return self.client.ws.ssrc

    # Protocol related functions

    def __call__(self, *args, **kwargs):
        return self

    def connection_made(
        self, transport: Any
    ) -> None:  # This is Any because mypy keeps complaining
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        self.queue.put_nowait(data)

    async def sendto(self, data: bytes, addr: Tuple[str, int]) -> None:
        if not hasattr(self, "transport"):
            return

        self.transport.sendto(data, addr)

        with contextlib.suppress(ConnectionResetError):
            await self.drain()

    async def drain(
        self,
    ):  # From asyncio.StreamWriter.drain but without the reader stuff
        if self.transport.is_closing():
            await asyncio.sleep(0)

        await self._drain_helper()

    async def read(self) -> bytes:
        return await self.queue.get()

    # Voice related functions

    def create_secret_box(self) -> nacl.secret.SecretBox:
        if self._secret_box:
            return self._secret_box

        self._secret_box = nacl.secret.SecretBox(bytes(self.client.ws.secret_key))
        return self._secret_box

    def increment(self, attr: str, value: int, max_value: int) -> None:
        val = getattr(self, attr)
        val += value

        if val >= max_value:
            setattr(self, attr, 0)

    def create_rtp_header(self) -> bytearray:
        packet = bytearray(12)

        packet[0] = 0x80
        packet[1] = 0x78

        struct.pack_into(">H", packet, 2, self.sequence)
        struct.pack_into(">I", packet, 4, self.timestamp)
        struct.pack_into(">I", packet, 8, self.ssrc)

        return packet

    def generate_xsalsa20_poly1305_nonce(self, header: bytes) -> bytes:
        nonce = bytearray(24)
        nonce[:12] = header

        return nonce

    def generate_xsalsa20_poly1305_suffix_nonce(self) -> bytes:
        return nacl.secret.random(24)

    def generate_xsalsa20_poly1305_lite_nonce(self) -> bytes:
        nonce = bytearray(24)
        nonce[:4] = struct.pack(">I", self.lite_nonce)

        self.increment("lite_nonce", 1, 4294967294)
        return nonce

    def encrypt_xsalsa20_poly1305(self, header: bytes, data: bytes) -> bytes:
        box = self.create_secret_box()
        nonce = self.generate_xsalsa20_poly1305_nonce(header)

        return header + box.encrypt(data, nonce)

    def encrypt_xsalsa20_poly1305_suffix(self, header: bytes, data: bytes) -> bytes:
        box = self.create_secret_box()
        nonce = self.generate_xsalsa20_poly1305_suffix_nonce()

        return header + box.encrypt(data, nonce) + nonce

    def encrypt_xsalsa20_poly1305_lite(self, header: bytes, data: bytes) -> bytes:
        box = self.create_secret_box()
        nonce = self.generate_xsalsa20_poly1305_lite_nonce()

        return header + box.encrypt(data, nonce) + nonce[:4]

    def create_voice_packet(self, data: bytes) -> bytes:
        header = self.create_rtp_header()
        encrypt = self.supported_modes[self.client.ws.mode]  # type: ignore

        return encrypt(header, data)

    async def send_voice_packet(self) -> None:
        pass


class VoiceClient:
    def __init__(self, state: State, channel: VoiceChannel) -> None:
        self._state = state
        self._received_state_update = asyncio.Event()
        self._received_server_update = asyncio.Event()

        self.channel = channel
        self.session_id: Optional[str] = None
        self.endpoint: Optional[str] = None
        self.token: Optional[str] = None
        self.ws = VoiceWebSocketClient(self, self.channel.guild.id, self._state.user.id)  # type: ignore
        self.protocol = VoiceProtocol(self)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._state.loop

    async def voice_state_update(self, data: Dict):
        payload = data["d"]
        self.session_id = payload["session_id"]

        self._received_state_update.set()

    async def voice_server_update(self, data: Dict):
        payload = data["d"]
        self.endpoint = payload["endpoint"]
        self.token = payload["token"]

        self._received_server_update.set()

    async def connect(self) -> None:
        await self.channel.guild.change_voice_state(channel=self.channel)

        futures = [
            self._received_server_update.wait(),
            self._received_state_update.wait(),
        ]
        await asyncio.wait(futures, return_when=asyncio.ALL_COMPLETED)

        await self.ws.connect()
