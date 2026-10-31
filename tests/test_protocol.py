import pytest

from pyredis.protocol import (
    INCOMPLETE,
    MAX_ARRAY_LENGTH,
    MAX_BULK_LENGTH,
    MAX_LINE_LENGTH,
    NULL_ARRAY,
    ErrorReply,
    ProtocolError,
    RESPError,
    SimpleString,
    _parse_int,
    _read_line,
    parse,
    serialize,
)


# Group 1: Basic Types
def test_simple_string():
    assert serialize(SimpleString("OK")) == b"+OK\r\n"


def test_error_reply():
    assert serialize(ErrorReply("ERR bad")) == b"-ERR bad\r\n"


def test_int():
    assert serialize(5) == b":5\r\n"


def test_str():
    assert serialize("hi") == b"$2\r\nhi\r\n"


def test_bytes():
    assert serialize(b"hi") == b"$2\r\nhi\r\n"


def test_null_str():
    assert serialize("") == b"$0\r\n\r\n"


def test_none():
    assert serialize(None) == b"$-1\r\n"


def test_null_array():
    assert serialize(NULL_ARRAY) == b"*-1\r\n"


# Group 2: Arrays
def test_empty_list():
    assert serialize([]) == b"*0\r\n"


def test_list():
    assert serialize([1, 2]) == b"*2\r\n:1\r\n:2\r\n"


def test_list_with_none():
    assert serialize(["a", None]) == b"*2\r\n$1\r\na\r\n$-1\r\n"


def test_nested_lists():
    assert serialize([1, [b"a", None]]) == b"*2\r\n:1\r\n*2\r\n$1\r\na\r\n$-1\r\n"


# Group 3: Byte Length
def test_length():
    assert serialize("привет") == b"$12\r\n" + "привет".encode() + b"\r\n"
    assert len("привет") == 6
    assert len("привет".encode()) == 12


# Group 4: Raise Error
def test_bool():
    with pytest.raises(RESPError):
        serialize(True)


def test_simple_string_with_newline():
    with pytest.raises(RESPError):
        assert serialize(SimpleString("a\nb"))


def test_error_reply_with_cr():
    with pytest.raises(RESPError):
        assert serialize(ErrorReply("x\ry"))


def test_unsupported_type():
    with pytest.raises(RESPError):
        assert serialize({})


# Group 5: Equivalence
def test_equal():
    assert serialize("hi") == serialize(b"hi")


# INCOMPLETE


def test_incomplete_repr():
    assert repr(INCOMPLETE) == "INCOMPLETE"


def test_incomplete_is_not_none():
    assert INCOMPLETE is not None


# _read_line


def test_read_line_found():
    assert _read_line(b"+OK\r\n", 1) == (b"OK", 5)


def test_read_line_not_found():
    assert _read_line(b"+OK", 1) is INCOMPLETE


def test_read_line_split_crlf():
    assert _read_line(b"+OK\r", 1) is INCOMPLETE


def test_read_line_leaves_extra_bytes():
    assert _read_line(b"+OK\r\n+NEXT\r\n", 1) == (b"OK", 5)


def test_read_line_short_line_with_lots_of_extra_data():
    buffer = b"+OK\r\n" + b"x" * (MAX_LINE_LENGTH + 10)
    assert _read_line(buffer, 1) == (b"OK", 5)


def test_read_line_unfinished_line_too_long():
    with pytest.raises(ProtocolError):
        _read_line(b"a" * (MAX_LINE_LENGTH + 1), 0)


def test_read_line_finished_line_too_long():
    with pytest.raises(ProtocolError):
        _read_line(b"a" * (MAX_LINE_LENGTH + 1) + b"\r\n", 0)


# _parse_int


def test_parse_int_positive():
    assert _parse_int(b"5") == 5


def test_parse_int_negative():
    assert _parse_int(b"-5") == -5


def test_parse_int_zero():
    assert _parse_int(b"0") == 0


def test_parse_int_leading_zeros():
    assert _parse_int(b"007") == 7


def test_parse_int_rejects_bad_input():
    bad_inputs = [b"", b"-", b"abc", b" 5", b"5 ", b"+5", b"1_000", b"--5", b"1.5"]
    for bad in bad_inputs:
        with pytest.raises(ProtocolError):
            _parse_int(bad)


# Simple String


def test_parse_simple_string():
    assert parse(b"+OK\r\n") == (SimpleString("OK"), 5)


def test_parse_empty_simple_string():
    assert parse(b"+\r\n") == (SimpleString(""), 3)


def test_parse_simple_string_incomplete():
    assert parse(b"+OK") is INCOMPLETE


def test_parse_simple_string_invalid_utf8():
    with pytest.raises(ProtocolError):
        parse(b"+\xff\xfe\r\n")


# Error reply


def test_parse_error_reply():
    assert parse(b"-ERR bad\r\n") == (ErrorReply("ERR bad"), 10)


def test_parse_empty_error_reply():
    assert parse(b"-\r\n") == (ErrorReply(""), 3)


def test_parse_error_reply_incomplete():
    assert parse(b"-ERR") is INCOMPLETE


def test_parse_error_reply_invalid_utf8():
    with pytest.raises(ProtocolError):
        parse(b"-\xff\r\n")


# Integer


def test_parse_integer():
    assert parse(b":42\r\n") == (42, 5)


def test_parse_negative_integer():
    assert parse(b":-5\r\n") == (-5, 5)


def test_parse_integer_incomplete():
    assert parse(b":42") is INCOMPLETE


def test_parse_integer_only_type_byte():
    assert parse(b":") is INCOMPLETE


def test_parse_integer_garbage():
    with pytest.raises(ProtocolError):
        parse(b":abc\r\n")


def test_parse_integer_empty():
    with pytest.raises(ProtocolError):
        parse(b":\r\n")


# Bulk String


def test_parse_bulk_string():
    assert parse(b"$2\r\nhi\r\n") == (b"hi", 8)


def test_parse_empty_bulk_string():
    assert parse(b"$0\r\n\r\n") == (b"", 6)


def test_parse_null_bulk_string():
    assert parse(b"$-1\r\n") == (None, 5)


def test_parse_bulk_string_with_crlf_inside():
    assert parse(b"$5\r\na\r\nbc\r\n") == (b"a\r\nbc", 11)


def test_parse_bulk_string_stays_bytes():
    value, _ = parse("$12\r\nпривет\r\n".encode())
    assert value == "привет".encode()
    assert isinstance(value, bytes)


def test_parse_bulk_string_incomplete_header():
    assert parse(b"$2") is INCOMPLETE


def test_parse_bulk_string_incomplete_data():
    assert parse(b"$2\r\nh") is INCOMPLETE


def test_parse_bulk_string_incomplete_terminator():
    assert parse(b"$2\r\nhi\r") is INCOMPLETE


def test_parse_bulk_string_bad_terminator():
    with pytest.raises(ProtocolError):
        parse(b"$2\r\nhiXX")


def test_parse_bulk_string_negative_length():
    with pytest.raises(ProtocolError):
        parse(b"$-2\r\n")


def test_parse_bulk_string_over_limit():
    header = b"$" + str(MAX_BULK_LENGTH + 1).encode("ascii") + b"\r\n"
    with pytest.raises(ProtocolError):
        parse(header)


def test_parse_bulk_string_at_limit_waits_for_data():
    header = b"$" + str(MAX_BULK_LENGTH).encode("ascii") + b"\r\n"
    assert parse(header) is INCOMPLETE


def test_parse_bulk_string_invalid_length():
    with pytest.raises(ProtocolError):
        parse(b"$abc\r\n")


# Array


def test_parse_empty_array():
    assert parse(b"*0\r\n") == ([], 4)


def test_parse_null_array():
    assert parse(b"*-1\r\n") == (NULL_ARRAY, 5)


def test_parse_flat_array():
    assert parse(b"*2\r\n:1\r\n:2\r\n") == ([1, 2], 12)


def test_parse_nested_array():
    assert parse(b"*1\r\n*1\r\n:1\r\n") == ([[1]], 12)


def test_parse_array_with_mixed_types():
    msg = b"*4\r\n+OK\r\n-ERR x\r\n$-1\r\n$2\r\nhi\r\n"
    expected = [SimpleString("OK"), ErrorReply("ERR x"), None, b"hi"]
    assert parse(msg) == (expected, len(msg))


def test_parse_real_command():
    msg = b"*3\r\n$3\r\nSET\r\n$4\r\nname\r\n$3\r\nBob\r\n"
    assert parse(msg) == ([b"SET", b"name", b"Bob"], len(msg))
    assert len(msg) == 32


def test_parse_array_incomplete_header():
    assert parse(b"*2") is INCOMPLETE


def test_parse_array_missing_elements():
    assert parse(b"*2\r\n:1\r\n") is INCOMPLETE


def test_parse_array_incomplete_last_element():
    assert parse(b"*2\r\n:1\r\n$2\r\nh") is INCOMPLETE


def test_parse_array_negative_count():
    with pytest.raises(ProtocolError):
        parse(b"*-2\r\n")


def test_parse_array_over_limit():
    header = b"*" + str(MAX_ARRAY_LENGTH + 1).encode("ascii") + b"\r\n"
    with pytest.raises(ProtocolError):
        parse(header)


def test_parse_array_invalid_count():
    with pytest.raises(ProtocolError):
        parse(b"*abc\r\n")


def test_parse_array_with_malformed_element():
    with pytest.raises(ProtocolError):
        parse(b"*2\r\n:1\r\n?\r\n")


# Nesting depth


def test_parse_nesting_at_limit():
    msg = b"*1\r\n" * 32 + b":1\r\n"
    _value, pos = parse(msg)
    assert pos == len(msg)


def test_parse_nesting_over_limit():
    msg = b"*1\r\n" * 33 + b":1\r\n"
    with pytest.raises(ProtocolError):
        parse(msg)


def test_parse_very_deep_nesting_does_not_crash():
    msg = b"*1\r\n" * 5000
    with pytest.raises(ProtocolError):
        parse(msg)


# Dispatcher / Parser


def test_parse_empty_buffer():
    assert parse(b"") is INCOMPLETE


def test_parse_unknown_type_byte():
    with pytest.raises(ProtocolError):
        parse(b"?\r\n")


def test_parse_pos_at_end_of_buffer():
    assert parse(b":1\r\n", 4) is INCOMPLETE


# Several messages in one buffer
def test_parse_first_of_two_messages():
    assert parse(b":1\r\n:2\r\n") == (1, 4)


def test_parse_second_of_two_messages():
    assert parse(b":1\r\n:2\r\n", 4) == (2, 8)


def test_parse_leaves_extra_bytes_untouched():
    assert parse(b"+OK\r\n+NEXT\r\n") == (SimpleString("OK"), 5)


def test_parse_all_messages_in_a_loop():
    buffer = serialize([b"PING"]) + serialize([b"ECHO", b"hi"]) + b"*1\r\n$4\r\nPI"
    results = []
    pos = 0
    while True:
        result = parse(buffer, pos)
        if result is INCOMPLETE:
            break
        value, pos = result
        results.append(value)
    assert results == [[b"PING"], [b"ECHO", b"hi"]]
    assert buffer[pos:] == b"*1\r\n$4\r\nPI"


# Round trip
def test_round_trip_values():
    values = [
        SimpleString("OK"),
        SimpleString(""),
        ErrorReply("ERR x"),
        0,
        -7,
        123456789,
        None,
        NULL_ARRAY,
        b"hi",
        b"",
        b"a\r\nb",
        [],
        [1, 2, 3],
        [1, [b"a", None]],
        [[], [[]]],
        [SimpleString("OK"), NULL_ARRAY, b"x", -1],
    ]
    for value in values:
        encoded = serialize(value)
        assert parse(encoded) == (value, len(encoded))


def test_round_trip_str_comes_back_as_bytes():
    encoded = serialize("привет")
    assert parse(encoded) == ("привет".encode(), len(encoded))


# Prefix test
def test_every_prefix_of_a_nested_message_is_incomplete():
    msg = serialize([b"SET", b"name", [1, None, SimpleString("OK")], b"a\r\nb"])
    for i in range(len(msg)):
        assert parse(msg[:i]) is INCOMPLETE, f"prefix of length {i} was not INCOMPLETE"
    assert parse(msg)[1] == len(msg)


def test_every_prefix_of_each_simple_type_is_incomplete():
    messages = [
        b"+OK\r\n",
        b"-ERR bad\r\n",
        b":-42\r\n",
        b"$-1\r\n",
        b"$0\r\n\r\n",
        b"$5\r\nhello\r\n",
        b"*-1\r\n",
        b"*0\r\n",
    ]
    for msg in messages:
        for i in range(len(msg)):
            assert parse(msg[:i]) is INCOMPLETE, f"{msg!r} cut at {i}"
