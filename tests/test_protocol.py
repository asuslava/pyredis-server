from pyredis.protocol import *
import pytest

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


#Group 2: Arrays
def test_empty_list():
    assert serialize([]) == b"*0\r\n"

def test_list():
    assert serialize([1, 2]) == b"*2\r\n:1\r\n:2\r\n"

def test_list_with_none():
    assert serialize(["a", None]) == b"*2\r\n$1\r\na\r\n$-1\r\n"

def test_nested_lists():
    assert serialize([1, [b"a", None]]) == b"*2\r\n:1\r\n*2\r\n$1\r\na\r\n$-1\r\n"


#Group 3: Byte Length
def test_length():
    assert serialize("привет") == b"$12\r\n" + "привет".encode("utf-8") + b"\r\n"
    assert len("привет") == 6
    assert len("привет".encode("utf-8")) == 12


#Group 4: Raise Error
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


#Group 5: Equivalence
def test_equal():
    assert serialize("hi") == serialize(b"hi")