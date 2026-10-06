# ============================================================
# TODO (limits)
# ============================================================
# TODO: MAX_LINE_LENGTH      - longest allowed header / simple line
# TODO: MAX_BULK_LENGTH      - e.g. 512 MB, like real Redis
# TODO: MAX_ARRAY_LENGTH     - max elements in one array
# TODO: MAX_NESTING_DEPTH    - protects recursion from deeply nested arrays


# ============================================================
# TODO (INCOMPLETE marker), place it next to NULL_ARRAY
# ============================================================
# TODO: class Incomplete with __slots__ = () and __repr__
# TODO: INCOMPLETE = Incomplete()
# TODO: ParseResult = tuple[Any, int] | Incomplete   (type alias)


# ============================================================
# TODO (parser helpers), place below serialize
# ============================================================
# TODO: _read_line(buffer, pos)
#       - find b"\r\n" starting at pos
#       - not found and the line is already longer than MAX_LINE_LENGTH -> ProtocolError
#       - not found -> INCOMPLETE
#       - found -> (line_without_crlf, position_after_crlf)
#
# TODO: _parse_int(line)
#       - bytes -> int
#       - ValueError -> ProtocolError


# ============================================================
# TODO (one handler per type)
# every handler: (buffer, pos_after_type_byte, depth) -> (value, new_pos) or INCOMPLETE
# ============================================================
# TODO: _parse_simple_string
#       - read line, decode utf-8, wrap in SimpleString
#       - UnicodeDecodeError -> ProtocolError
#
# TODO: _parse_error
#       - same as simple string, but wrap in ErrorReply
#
# TODO: _parse_integer
#       - read line, convert with _parse_int
#
# TODO: _parse_bulk_string
#       - read length line, convert with _parse_int
#       - -1 -> (None, pos)
#       - below -1 or above MAX_BULK_LENGTH -> ProtocolError
#       - not enough bytes for data + CRLF -> INCOMPLETE
#       - the 2 bytes after the data are not CRLF -> ProtocolError
#       - read by length (data may contain \r\n), keep as bytes, don't decode
#
# TODO: _parse_array
#       - read count line, convert with _parse_int
#       - -1 -> NULL_ARRAY
#       - 0 -> []
#       - below -1 or above MAX_ARRAY_LENGTH -> ProtocolError
#       - loop `count` times calling _parse_value with depth + 1
#       - check `is INCOMPLETE` BEFORE unpacking each result
#       - any element INCOMPLETE -> whole array INCOMPLETE


# ============================================================
# TODO (dispatcher)
# ============================================================
# TODO: _parse_value(buffer, pos, depth)
#       - depth > MAX_NESTING_DEPTH -> ProtocolError
#       - pos >= len(buffer) -> INCOMPLETE (empty buffer is not an error)
#       - look at buffer[pos]: + - : $ *
#       - call the matching handler with pos + 1
#       - unknown type byte -> ProtocolError


# ============================================================
# TODO (public API)
# ============================================================
# TODO: parse(buffer, pos=0)
#       - just calls _parse_value(buffer, pos, 0)
#       - returns (value, new_pos) or INCOMPLETE
#       - never modifies the buffer


# ============================================================
# TODO (checks before moving on)
# ============================================================
# TODO: tests for every handler (hand-written bytes)
# TODO: round trip: parse(serialize(x)) == x   (strings come back as bytes)
# TODO: every shorter prefix of a valid message -> INCOMPLETE, never an error
# TODO: two commands glued together -> returned pos points to the start of the second
# TODO: malformed input -> ProtocolError (bad type byte, bad length, missing CRLF)