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
import enum

from . import _opus

if TYPE_CHECKING:
    from .wsclient import VoiceWebSocketClient
    from .client import VoiceClient
    from .listeners import AudioListener

    Encrypter = Callable[[bytes, bytes], bytes]
    Decrypter = Callable[["RTPPacket"], bytes]

__all__ = ("VoiceProtocol",)

UNSIGNED_INT = struct.Struct(">I")
UNSIGNED_SHORT = struct.Struct(">H")
UNSIGNED_CHAR = struct.Struct(">B")
SHORT = struct.Struct(">H")


class RTPPacket:
    __slots__ = ("sequence", "timestamp", "ssrc", "extended", "cc", "payload", "header", "csrcs", "data")
    HEADER = struct.Struct(">xxHII")

    def __init__(self, payload: bytes) -> None:
        self.sequence, self.timestamp, self.ssrc = self.HEADER.unpack_from(payload)
        self.extended = bool(payload[0] >> 4 & 1)
        self.cc = payload[0] & 0x0F
        self.payload = payload[self.HEADER.size :]
        self.header = payload[: self.HEADER.size]

        self.csrcs: Tuple[Any, ...] = ()
        if self.cc:
            fmt = ">{}I".format(self.cc)
            offset = struct.calcsize(fmt) + 12

            self.csrcs = struct.unpack_from(fmt, self.payload, offset)
            self.payload = payload[offset:]

    def parse_extension_header(self, data: bytes) -> bytes:
        return data


class VoiceProtocol(asyncio.streams.FlowControlMixin, asyncio.DatagramProtocol):
    if TYPE_CHECKING:
        _loop: asyncio.AbstractEventLoop
        _paused: bool

        async def _drain_helper(self) -> None:
            ...

    SUPPORTED_MODES = [
        "xsalsa20_poly1305",
        "xsalsa20_poly1305_suffix",
        "xsalsa20_poly1305_lite",
    ]

    def __init__(self, client: VoiceClient):
        self.client = client
        self.queue = asyncio.Queue[bytes]()
        self.timestamp = 0
        self.sequence = 0
        self.lite_nonce = 0
        self.encoder = _opus.OpusEncoder()
        self.decoder = _opus.OpusDecoder()
        self.encrypters: Dict[str, Encrypter] = {
            "xsalsa20_poly1305": self.encrypt_xsalsa20_poly1305,
            "xsalsa20_poly1305_suffix": self.encrypt_xsalsa20_poly1305_suffix,
            "xsalsa20_poly1305_lite": self.encrypt_xsalsa20_poly1305_lite,
        }
        self.decrypters: Dict[str, Decrypter] = {
            "xsalsa20_poly1305": self.decrypt_xsalsa20_poly1305,
            "xsalsa20_poly1305_suffix": self.decrypt_xsalsa20_poly1305_suffix,
            "xsalsa20_poly1305_lite": self.decrypt_xsalsa20_poly1305_lite,
        }

        self._secret_box: Optional[nacl.secret.SecretBox] = None
        super().__init__()

    @property
    def websocket(self) -> VoiceWebSocketClient:
        return self.client.ws

    @property
    def ssrc(self) -> Optional[int]:
        return self.websocket.ssrc

    @property
    def listener(self) -> Optional[AudioListener]:
        return self.client._listener

    # Protocol related functions

    def __call__(self, *args, **kwargs) -> VoiceProtocol:
        return self

    def connection_made(self, transport: Any) -> None:  # This is Any because mypy keeps complaining
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        self.queue.put_nowait(data)

        if self.listener:
            ssrc = UNSIGNED_INT.unpack_from(data, 8)[0]
            user_data = self.websocket.get_user(ssrc)

            if not user_data:
                return

            if not self.listener.filter(user_data):
                return

            packet = RTPPacket(data)
            packet.payload = self.decrypt_voice_packet(packet)

            self.listener.feed(packet)

    async def write(self, data: bytes) -> None:
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

        UNSIGNED_SHORT.pack_into(packet, 2, self.sequence)
        UNSIGNED_INT.pack_into(packet, 4, self.timestamp)
        UNSIGNED_INT.pack_into(packet, 8, self.ssrc)

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

    def decrypt_xsalsa20_poly1305(self, packet: RTPPacket) -> bytes:
        nonce = bytearray(24)
        nonce[:12] = packet.header

        return self.decrypt(packet.payload, nonce, packet)

    def decrypt_xsalsa20_poly1305_suffix(self, packet: RTPPacket) -> bytes:
        nonce = packet.payload[-24:]
        return self.decrypt(packet.payload[:-24], nonce, packet)

    def decrypt_xsalsa20_poly1305_lite(self, packet: RTPPacket) -> bytes:
        nonce = bytearray(24)
        nonce[:4] = packet.payload[-4:]

        return self.decrypt(packet.payload[:-4], nonce, packet)

    def encrypt(self, data: bytes, nonce: bytes) -> bytes:
        box = self.create_secret_box()
        return box.encrypt(bytes(data), bytes(nonce)).ciphertext

    def decrypt(self, data: bytes, nonce: bytes, packet: RTPPacket) -> bytes:
        box = self.create_secret_box()
        ret = box.decrypt(bytes(data), bytes(nonce))

        if packet.extended:
            return packet.parse_extension_header(ret)

        return ret

    def create_voice_packet(self, data: bytes) -> bytes:
        assert self.websocket.mode is not None

        header = self.create_rtp_header()
        encoded = self.encoder.encode(data, 960)

        encrypt = self.encrypters[self.websocket.mode]
        return encrypt(header, encoded)

    def decrypt_voice_packet(self, packet: RTPPacket) -> bytes:
        assert self.websocket.mode is not None

        decypter = self.decrypters[self.websocket.mode]
        return decypter(packet)

    async def send_voice_packet(self, data: bytes) -> None:
        self.increment("sequence", 1, 0xFFFF)

        packet = self.create_voice_packet(data)
        await self.write(packet)

        self.increment("timestamp", 960, 0xFFFFFFFF)

    async def send_raw_voice_packet(self, data: bytes) -> None:
        await self.write(data)
