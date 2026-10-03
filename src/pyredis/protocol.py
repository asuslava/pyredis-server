from dataclasses import dataclass
from typing import Any


class RESPError(Exception):
    pass

class ProtocolError(RESPError):
    pass

@dataclass(frozen=True, slots=True)
class SimpleString:
    value : str

@dataclass(frozen=True, slots=True)
class ErrorReply:
    message : str

class NullArray:
    __slots__ = ()

    def __repr__(self) -> str:
        return "NullArray"

NULL_ARRAY = NullArray()

def _check_line_safe(text: str) -> None:
    if "\r" in text or "\n" in text:
        raise RESPError(f"Data must not contain CR or LF: {text!r}")

def serialize(data: Any) -> bytes:

    if data is None:
        return b"$-1\r\n"

    if data is NULL_ARRAY:
        return b"*-1\r\n"

    if type(data) is bool:
        raise RESPError("Booleans are not supported in RESP2")

    if isinstance(data, SimpleString):
        _check_line_safe(data.value)
        return f"+{data.value}\r\n".encode("utf-8")

    if isinstance(data, ErrorReply):
        _check_line_safe(data.message)
        return f"-{data.message}\r\n".encode("utf-8")

    if isinstance(data, int):
        return f":{data}\r\n".encode("ascii")

    if isinstance(data, (str, bytes)):
        if isinstance(data, str):
            raw = data.encode("utf-8")
        else:
            raw = data
        return f"${len(raw)}\r\n".encode("ascii") + raw + b"\r\n"

    if isinstance(data, (list, tuple)):
        parts = [f"*{len(data)}\r\n".encode("ascii")]
        for i in data:
            parts.append(serialize(i))

        return b"".join(parts)

    raise RESPError(f"Unknown type: {type(data)}")
