from __future__ import annotations
import asyncio
import time

from typing import TYPE_CHECKING, Callable, Optional, Protocol, BinaryIO, Union
import wave

from . import _opus

if TYPE_CHECKING:
    from .protocol import VoiceProtocol, RTPPacket
    from .wsclient import UserVoiceData

__all__ = (
    "AudioDestination",
    "OpusAudioDestination",
    "WaveAudioDestination",
    "AudioListener",
)


class AudioDestination(Protocol):
    async def write(self, packet: RTPPacket) -> None:
        ...

    def close(self) -> None:
        ...


class OpusAudioDestination(AudioDestination):
    def __init__(self, stream: Union[BinaryIO, str]) -> None:
        self.decoder = _opus.OpusDecoder()

        if isinstance(stream, str):
            self.stream = open(stream, "wb")
        else:
            self.stream = stream

    async def write(self, packet: RTPPacket) -> None:
        decoded = self.decoder.decode(packet.data)
        await asyncio.to_thread(self.stream.write, decoded)

    def close(self) -> None:
        self.stream.close()


class WaveAudioDestination(AudioDestination):
    def __init__(self, stream: str) -> None:
        self.stream: wave.Wave_write = wave.open(stream, "wb")

        self.stream.setnchannels(_opus.CHANNELS)
        self.stream.setsampwidth(_opus.SAMPLE_SIZE // _opus.CHANNELS)
        self.stream.setframerate(_opus.SAMPLE_RATE)

    async def write(self, packet: RTPPacket) -> None:
        await asyncio.to_thread(self.stream.writeframes, packet.data)

    def close(self) -> None:
        self.stream.close()


class AudioListener:
    def __init__(self, protocol: VoiceProtocol, dest: AudioDestination):
        self.protocol = protocol
        self.destination = dest
        self.queue = asyncio.Queue["RTPPacket"]()
        self.loop = protocol._loop

        self._waiter: Optional[asyncio.Task[AudioDestination]] = None
        self._filter = lambda user: True

    def feed(self, packet: RTPPacket) -> None:
        self.queue.put_nowait(packet)

    @property
    def filter(self) -> Callable[[UserVoiceData], bool]:
        return self._filter

    @filter.setter
    def filter(self, value: Callable[[UserVoiceData], bool]):
        self._filter = value

    async def _listen(
        self, duration: int, *, timeout: Optional[float]
    ) -> AudioDestination:
        last_spoke = 0.0
        end = time.time() + duration

        while time.time() < end:
            try:
                data = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                break

            if timeout is not None:
                if time.time() - last_spoke > timeout and last_spoke != 0:
                    break

            last_spoke = time.time()
            await self.destination.write(data)

        self.destination.close()
        return self.destination

    def listen(
        self, duration: int, *, timeout: Optional[float] = None
    ) -> AudioListener:
        self._waiter = self.loop.create_task(self._listen(duration, timeout=timeout))
        return self

    def is_listening(self) -> bool:
        return self._waiter is not None and self._waiter.done()
