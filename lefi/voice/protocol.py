from __future__ import annotations

import contextlib
import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
    cast,
)
import struct
import nacl.secret

from . import _opus
from .wsclient import VoiceWebSocketClient

if TYPE_CHECKING:
    from .client import VoiceClient

    Encrypter = Callable[[bytes, bytes], bytes]

__all__ = ("VoiceProtocol",)


class VoiceProtocol(asyncio.streams.FlowControlMixin, asyncio.DatagramProtocol):
    if TYPE_CHECKING:
        _loop: asyncio.AbstractEventLoop
        _paused: bool

        async def _drain_helper(self) -> None:
            ...

    def __init__(self, client: VoiceClient):
        self.client = client
        self.queue = asyncio.Queue[bytes]()
        self.timestamp = 0
        self.sequence = 0
        self.lite_nonce = 0
        self.encoder = _opus.OpusEncoder()
        self.supported_modes: Dict[str, Encrypter] = {
            "xsalsa20_poly1305": self.encrypt_xsalsa20_poly1305,
            "xsalsa20_poly1305_suffix": self.encrypt_xsalsa20_poly1305_suffix,
            "xsalsa20_poly1305_lite": self.encrypt_xsalsa20_poly1305_lite,
        }

        self._secret_box: Optional[nacl.secret.SecretBox] = None
        super().__init__()

    @property
    def websocket(self) -> VoiceWebSocketClient:
        return self.client.ws

    @property
    def ssrc(self) -> Optional[int]:
        return self.websocket.ssrc

    # Protocol related functions

    def __call__(self, *args, **kwargs) -> VoiceProtocol:
        return self

    def connection_made(
        self, transport: Any
    ) -> None:  # This is Any because mypy keeps complaining
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        self.queue.put_nowait(data)

    async def sendto(self, data: bytes) -> None:
        if not hasattr(self, "transport"):
            return

        addr = self.websocket.remote_addr
        self.transport.sendto(data, addr)

        with contextlib.suppress(ConnectionResetError):
            await self.drain()

    async def drain(
        self,
    ) -> None:  # From asyncio.StreamWriter.drain but without the reader stuff
        if self.transport.is_closing():
            await asyncio.sleep(0)

        await self._drain_helper()

    async def read(self) -> bytes:
        return await self.queue.get()

    # Voice related functions

    def create_secret_box(self) -> nacl.secret.SecretBox:
        if self._secret_box:
            return self._secret_box

        self._secret_box = nacl.secret.SecretBox(bytes(self.websocket.secret_key))
        return self._secret_box

    def increment(self, attr: str, value: int, max_value: int) -> None:
        val = getattr(self, attr)
        if val + value >= max_value:
            setattr(self, attr, 0)
        else:
            setattr(self, attr, val + value)

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

        self.increment("lite_nonce", 1, 0xFFFFFFFF)
        return nonce

    def encrypt_xsalsa20_poly1305(self, header: bytes, data: bytes) -> bytes:
        nonce = self.generate_xsalsa20_poly1305_nonce(header)
        return header + self.encrypt(data, nonce)

    def encrypt_xsalsa20_poly1305_suffix(self, header: bytes, data: bytes) -> bytes:
        nonce = self.generate_xsalsa20_poly1305_suffix_nonce()
        return header + self.encrypt(data, nonce) + nonce

    def encrypt_xsalsa20_poly1305_lite(self, header: bytes, data: bytes) -> bytes:
        nonce = self.generate_xsalsa20_poly1305_lite_nonce()
        return header + self.encrypt(data, nonce) + nonce[:4]

    def encrypt(self, data: bytes, nonce: bytes) -> bytes:
        box = self.create_secret_box()
        return box.encrypt(bytes(data), bytes(nonce)).ciphertext

    def create_voice_packet(self, data: bytes) -> bytes:
        header = self.create_rtp_header()
        encoded = self.encoder.encode(data, 960)

        encrypt = self.supported_modes[self.websocket.mode]  # type: ignore
        return encrypt(header, encoded)

    async def send_voice_packet(self, data: bytes) -> None:
        self.increment("sequence", 1, 0xFFFF)

        packet = self.create_voice_packet(data)
        await self.sendto(packet)

        self.increment("timestamp", 960, 0xFFFFFFFF)

    async def send_raw_voice_packet(self, data: bytes) -> None:
        await self.sendto(data)
