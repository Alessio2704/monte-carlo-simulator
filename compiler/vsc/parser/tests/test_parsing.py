import pytest

from vsc.parser.parser import parse_valuascript


# def test_parse_only_iterations():
#     script = "@iterations = 1"
#     parsed = parse_valuascript(script)
#     assert parsed.directives[0] is not None
#     assert parsed.directives[0].name == "iterations"
#     assert parsed.directives[0].value.value == 1
