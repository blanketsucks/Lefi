from enum import IntEnum
from typing import Any, Dict, List, NamedTuple
import ctypes
import struct
import sys
import pathlib

c_int_ptr = ctypes.POINTER(ctypes.c_int)
c_int16_ptr = ctypes.POINTER(ctypes.c_int16)
c_float_ptr = ctypes.POINTER(ctypes.c_float)


class OpusEncoderStruct(ctypes.Structure):
    pass


class OpusDecoderStruct(ctypes.Structure):
    pass


OpusEncoderPointer = ctypes.POINTER(OpusEncoderStruct)
OpusDecoderPointer = ctypes.POINTER(OpusDecoderStruct)


class CFuncWrapper(NamedTuple):
    name: str
    args: List[Any]
    returntype: Any


CHANNELS = 2
SAMPLE_RATE = 48000
FRAME_DURATION = 20
FRAME_SIZE = FRAME_DURATION * SAMPLE_RATE // 1000
PACKET_SIZE = FRAME_SIZE * CHANNELS * 2
BITRATE = 64000


class CTL(IntEnum):
    SET_BITRATE = 4002
    SET_BANDWIDTH = 4008
    SET_FEC = 4012
    SET_PLP = 4014
    SET_SIGNAL = 4024


libopus: ctypes.CDLL = None  # type: ignore
_bin = pathlib.Path(__file__).parent / "bin"
exports: Dict[str, CFuncWrapper] = {
    "opus_get_version_string": CFuncWrapper(
        "opus_get_version_string",
        [],
        ctypes.c_char_p,
    ),
    "opus_strerror": CFuncWrapper(
        "opus_strerror",
        [ctypes.c_int],
        ctypes.c_char_p,
    ),
    "opus_encoder_get_size": CFuncWrapper(
        "opus_encoder_get_size",
        [ctypes.c_int],
        ctypes.c_int,
    ),
    "opus_encoder_create": CFuncWrapper(
        "opus_encoder_create",
        [ctypes.c_int, ctypes.c_int, ctypes.c_int, c_int_ptr],
        OpusEncoderPointer,
    ),
    "opus_encoder_destroy": CFuncWrapper(
        "opus_encoder_destroy",
        [OpusEncoderPointer],
        None,
    ),
    "opus_encoder_ctl": CFuncWrapper(
        "opus_encoder_ctl",
        [OpusEncoderPointer, ctypes.c_int, ctypes.c_int],
        ctypes.c_int,
    ),
    "opus_encode": CFuncWrapper(
        "opus_encode",
        [
            OpusEncoderPointer,
            c_int16_ptr,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int32,
        ],
        ctypes.c_int32,
    ),
    "opus_decoder_get_size": CFuncWrapper(
        "opus_decoder_get_size",
        [ctypes.c_int],
        ctypes.c_int,
    ),
    "opus_decoder_create": CFuncWrapper(
        "opus_decoder_create",
        [ctypes.c_int, ctypes.c_int, c_int_ptr],
        OpusDecoderPointer,
    ),
    "opus_decoder_destroy": CFuncWrapper(
        "opus_decoder_destroy",
        [OpusDecoderPointer],
        None,
    ),
    "opus_decoder_ctl": CFuncWrapper(
        "opus_decoder_ctl",
        [OpusDecoderPointer, ctypes.c_int, ctypes.c_int],
        ctypes.c_int,
    ),
    "opus_decode": CFuncWrapper(
        "opus_decode",
        [
            OpusDecoderPointer,
            ctypes.c_char_p,
            ctypes.c_int32,
            c_int16_ptr,
            ctypes.c_int,
            ctypes.c_int,
        ],
        ctypes.c_int32,
    ),
    "opus_packet_get_nb_frames": CFuncWrapper(
        "opus_packet_get_nb_frames",
        [ctypes.c_char_p, ctypes.c_int],
        ctypes.c_int,
    ),
    "opus_packet_get_samples_per_frame": CFuncWrapper(
        "opus_packet_get_samples_per_frame",
        [ctypes.c_char_p, ctypes.c_int],
        ctypes.c_int,
    ),
    "opus_packet_get_nb_channels": CFuncWrapper(
        "opus_packet_get_nb_channels",
        [ctypes.c_char_p],
        ctypes.c_int,
    ),
    "opus_packet_get_bandwidth": CFuncWrapper(
        "opus_packet_get_bandwidth",
        [ctypes.c_char_p],
        ctypes.c_int,
    ),
}


def get_cpu_architecture():
    size = struct.calcsize("P") * 8
    return "x64" if size > 32 else "x86"


def find_opus():
    if sys.platform == "win32":
        target = get_cpu_architecture()
        lib = _bin / f"libopus-0.{target}.dll"
        return ctypes.cdll.LoadLibrary(str(lib))

    return ctypes.cdll.LoadLibrary("opus")


def load_opus_from_dll(lib: ctypes.CDLL) -> None:
    for name, wrapped in exports.items():
        cfunc = getattr(lib, name)

        cfunc.argtypes = wrapped.args
        cfunc.restype = wrapped.returntype


def load_opus():
    global libopus

    lib = find_opus()
    load_opus_from_dll(lib)

    libopus = lib


def get_version_string() -> str:
    if not libopus:
        load_opus()

    return libopus.opus_get_version_string().decode("utf-8")


def get_error_string(code: int) -> str:
    return libopus.opus_strerror(code).decode("utf-8")


def get_packet_nb_frames(data: bytes) -> int:
    return libopus.opus_packet_get_nb_frames(data, len(data))


def get_packet_samples_per_frame(data: bytes) -> int:
    return libopus.opus_packet_get_nb_samples(data, len(data))


def get_packet_nb_channels(data: bytes) -> int:
    return libopus.opus_packet_get_nb_channels(data)


def get_packet_bandwidth(data: bytes) -> int:
    return libopus.opus_packet_get_bandwidth(data)


def create_int16_buffer(size: int) -> ctypes.Array[ctypes.c_int16]:
    return (ctypes.c_int16 * size)()


class OpusEncoder:
    def __init__(self) -> None:
        self._struct = self._create_encoder_struct()

        self.set_bitrate(BITRATE)
        self.set_fec(True)
        self.set_bandwidth(1105)
        self.set_signal(-1000)
        self.set_packet_loss_percentage(150)

    def _create_encoder_struct(self) -> OpusEncoderStruct:
        if not libopus:
            load_opus()

        ref = ctypes.byref(ctypes.c_int())
        encoder = libopus.opus_encoder_create(SAMPLE_RATE, CHANNELS, 2049, ref)
        return encoder

    def set_bitrate(self, bitrate: int) -> int:
        libopus.opus_encoder_ctl(self._struct, CTL.SET_BITRATE, bitrate)
        return bitrate

    def set_bandwidth(self, bandwidth: int) -> int:
        libopus.opus_encoder_ctl(self._struct, CTL.SET_BANDWIDTH, bandwidth)
        return bandwidth

    def set_signal(self, signal: int) -> int:
        libopus.opus_encoder_ctl(self._struct, CTL.SET_SIGNAL, signal)
        return signal

    def set_fec(self, fec: bool) -> bool:
        libopus.opus_encoder_ctl(self._struct, CTL.SET_FEC, int(fec))
        return fec

    def set_packet_loss_percentage(self, plp: int) -> int:
        libopus.opus_encoder_ctl(self._struct, CTL.SET_PLP, plp)
        return plp

    def encode(self, pcm: bytes, frames: int) -> bytes:
        pointer = ctypes.cast(pcm, c_int16_ptr)  # type: ignore

        size = len(pcm)
        buffer = ctypes.create_string_buffer(size)

        ret = libopus.opus_encode(self._struct, pointer, frames, buffer, size)
        return buffer.raw[:ret]

    def destroy(self) -> None:
        libopus.opus_encoder_destroy(self._struct)


class OpusDecoder:
    def __init__(self) -> None:
        self._struct = self._create_decoder_struct()

    def _create_decoder_struct(self) -> OpusDecoderStruct:
        if not libopus:
            load_opus()

        ref = ctypes.byref(ctypes.c_int())
        decoder = libopus.opus_decoder_create(SAMPLE_RATE, CHANNELS, ref)
        return decoder

    def decode(self, data: bytes) -> bytes:
        ...

    def destroy(self) -> None:
        libopus.opus_decoder_destroy(self._struct)