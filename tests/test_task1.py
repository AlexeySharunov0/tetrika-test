import pytest
from solution.task1 import strict

@strict
def sum_two(a: int, b: int) -> int:
    return a + b

@strict
def concat_strs(s1: str, s2: str) -> str:
    return s1 + s2

@strict
def is_positive(flag: bool) -> bool:
    return flag

@strict
def multiply_float(x: float, y: float) -> float:
    return x * y

def test_sum_two_correct():
    assert sum_two(1, 2) == 3

def test_sum_two_type_error():
    with pytest.raises(TypeError):
        sum_two(1, 2.5)
    with pytest.raises(TypeError):
        sum_two("1", 2)
    with pytest.raises(TypeError):
        sum_two(1, True)

def test_concat_strs_correct():
    assert concat_strs("hello", "world") == "helloworld"

def test_concat_strs_type_error():
    with pytest.raises(TypeError):
        concat_strs("hello", 5)

def test_is_positive_correct():
    assert is_positive(True) is True
    assert is_positive(False) is False

def test_is_positive_type_error():
    with pytest.raises(TypeError):
        is_positive(1)

def test_multiply_float_correct():
    assert multiply_float(1.5, 2.0) == 3.0

def test_multiply_float_type_error():
    with pytest.raises(TypeError):
        multiply_float(1, 2.0)
    with pytest.raises(TypeError):
        multiply_float(1.5, "2")

