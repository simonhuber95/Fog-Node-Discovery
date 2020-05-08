import pytest

# content of test_sample.py
def func(x):
    return x + 1


def test_1():
    assert func(3) == 5
    
def test_2():
    assert muste_be_right(1) == 1
    
def muste_be_right(y):
    return y