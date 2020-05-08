import pytest
import hello_thomas
 

# content of test_sample.py
thomas = hello_thomas.get_thomas()

def test_name():
    assert thomas["name"] == "Thomas"
    
def test_brille():
    assert thomas["brille"] == "Kastenbrille"
    
def test_alter():
    assert thomas["alter"] == "unknown"
    
def test_gruppe():
    assert thomas["gruppe"] == "pfl"