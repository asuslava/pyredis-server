from dataclasses import dataclass
from typing import Any

# Limits
MAX_LINE_LENGTH = 64 * 1024  # - longest allowed simple line
MAX_BULK_LENGTH = 512 * 1024 * 1024  # - e.g. 512 MB, like real Redis
MAX_ARRAY_LENGTH = 1024 * 1024  # - max elements in array
MAX_NESTING_DEPTH = 32  # - protects recursion from deeply nested arrays


# Exceptions
class RESPError(Exception):
    pass


class ProtocolError(RESPError):
    pass


# Types
@dataclass(frozen=True, slots=True)
class SimpleString:
    value: str


@dataclass(frozen=True, slots=True)
class ErrorReply:
    message: str


class NullArray:
    __slots__ = ()

    def __repr__(self) -> str:
        return "NullArray"


NULL_ARRAY = NullArray()


# Marker
class Incomplete:
    __slots__ = ()

    def __repr__(self) -> str:
        return "INCOMPLETE"


INCOMPLETE = Incomplete()
ParseResult = tuple[Any, int] | Incomplete


# Serializer
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
        return f"+{data.value}\r\n".encode()

    if isinstance(data, ErrorReply):
        _check_line_safe(data.message)
        return f"-{data.message}\r\n".encode()

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


# Parser
def _read_line(buffer: bytes, pos: int) -> tuple[bytes, int] | Incomplete:
    ending = buffer.find(b"\r\n", pos)

    if ending == -1:
        if len(buffer) - pos > MAX_LINE_LENGTH:
            raise ProtocolError("Line exceeds MAX_LINE_LENGTH")
        else:
            return INCOMPLETE

    if ending - pos > MAX_LINE_LENGTH:
        raise ProtocolError("Line exceeds MAX_LINE_LENGTH")

    return (buffer[pos:ending], ending + 2)


def _parse_int(line: bytes) -> int:
    negative = False
    digits = line

    if line.startswith(b"-"):
        digits = line[1:]
        negative = True

    if not digits.isdigit():
        raise ProtocolError(f"Invalid integer: {line!r}")

    value = int(digits)

    return -value if negative else value


def _parse_simple_string(buffer: bytes, pos: int, depth: int) -> ParseResult:
    result = _read_line(buffer, pos)

    if result is INCOMPLETE:
        return INCOMPLETE

    line, new_pos = result

    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocolError("Invalid UTF-8 in simple string") from exc

    return (SimpleString(text), new_pos)


def _parse_error(buffer: bytes, pos: int, depth: int) -> ParseResult:
    result = _read_line(buffer, pos)

    if result is INCOMPLETE:
        return INCOMPLETE

    line, new_pos = result

    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocolError("Invalid UTF-8 in error reply") from exc

    return (ErrorReply(text), new_pos)


def _parse_integer(buffer: bytes, pos: int, depth: int) -> ParseResult:
    result = _read_line(buffer, pos)

    if result is INCOMPLETE:
        return INCOMPLETE

    line, new_pos = result
    value = _parse_int(line)

    return (value, new_pos)


def _parse_bulk_string(buffer: bytes, pos: int, depth: int) -> ParseResult:
    result = _read_line(buffer, pos)

    if result is INCOMPLETE:
        return INCOMPLETE

    line, new_pos = result

    length = _parse_int(line)
    if length == -1:
        return (None, new_pos)
    if length < -1 or length > MAX_BULK_LENGTH:
        raise ProtocolError(f"Invalid bulk length: {length}")

    end = new_pos + length
    if len(buffer) < end + 2:
        return INCOMPLETE

    if buffer[end : end + 2] != b"\r\n":
        raise ProtocolError("Bulk string not terminated by CRLF")

    return (buffer[new_pos:end], end + 2)


def _parse_array(buffer: bytes, pos: int, depth: int) -> ParseResult:
    result = _read_line(buffer, pos)

    if result is INCOMPLETE:
        return INCOMPLETE

    line, new_pos = result

    count = _parse_int(line)
    if count == -1:
        return (NULL_ARRAY, new_pos)
    if count < -1 or count > MAX_ARRAY_LENGTH:
        raise ProtocolError(f"Invalid array count: {count}")

    items = []
    cur = new_pos

    for _ in range(count):
        element = _parse_value(buffer, cur, depth + 1)
        if element is INCOMPLETE:
            return INCOMPLETE

        item, cur = element
        items.append(item)

    return (items, cur)


# Dispatcher
def _parse_value(buffer: bytes, pos: int, depth: int) -> ParseResult:
    if depth > MAX_NESTING_DEPTH:
        raise ProtocolError(f"Nesting depth {depth} exceeds MAX_NESTING_DEPTH")

    if pos >= len(buffer):
        return INCOMPLETE

    type_byte = buffer[pos : pos + 1]
    if type_byte == b"+":
        return _parse_simple_string(buffer, pos + 1, depth)
    elif type_byte == b"-":
        return _parse_error(buffer, pos + 1, depth)
    elif type_byte == b":":
        return _parse_integer(buffer, pos + 1, depth)
    elif type_byte == b"$":
        return _parse_bulk_string(buffer, pos + 1, depth)
    elif type_byte == b"*":
        return _parse_array(buffer, pos + 1, depth)
    else:
        raise ProtocolError(f"Unknown type byte: {type_byte!r}")


def parse(buffer: bytes, pos: int = 0) -> ParseResult:
    """Returns (value, new_pos) or INCOMPLETE, raises ProtocolError"""
    return _parse_value(buffer, pos, 0)
