"""
Tests that the function signatures in the type stub file, the compiled
extension module, and the API documentation stay in sync. The stub file
is the source of truth: compiled functions cannot carry type annotations,
and Sphinx cannot read stubs, so the other two copies are checked
against it.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import emojet

API_RST = Path(__file__).parent.parent / "docs" / "api.rst"
STUB_FILE = Path(__file__).parent.parent / "src" / "emojet" / "_scan.pyi"


def stub_contents() -> tuple[list[ast.FunctionDef], list[str]]:
    functions = []
    data_names = []
    for node in ast.parse(STUB_FILE.read_text()).body:
        if isinstance(node, ast.FunctionDef):
            functions.append(node)
        elif isinstance(node, ast.AnnAssign):
            assert isinstance(node.target, ast.Name)
            data_names.append(node.target.id)
        else:
            assert isinstance(node, ast.ImportFrom)
    return functions, data_names


def stub_signature(function: ast.FunctionDef) -> str:
    header = ast.unparse(function).splitlines()[0]
    signature = header.removeprefix("def ").removesuffix(":")
    # ast.unparse writes defaults as "=" and strings with single quotes;
    # the docs use PEP 8's " = " and double quotes, matching the stub.
    # Neither character occurs with any other meaning in the signatures.
    return signature.replace("=", " = ").replace("'", '"')


def documented_signatures() -> dict[str, str]:
    matches = re.finditer(
        r"^\.\. function:: ((\w+)\(.*)$",
        API_RST.read_text(),
        flags=re.MULTILINE,
    )
    return {match[2]: match[1] for match in matches}


def assert_default_matches(parameter: inspect.Parameter, default: ast.expr) -> None:
    expected = ast.literal_eval(default)
    if parameter.default is ...:
        # PyO3 cannot represent tuple defaults in __text_signature__, so
        # the runtime signature shows "..." (Ellipsis) for them.
        assert isinstance(expected, tuple)
    else:
        assert parameter.default == expected


def test_stub_matches_module_exports():
    functions, data_names = stub_contents()
    stub_names = [function.name for function in functions] + data_names
    public_names = [
        name
        for name in dir(emojet)
        # Exclude the __future__ import that dir() picks up
        if not name.startswith("_") and name != "annotations"
    ]
    assert sorted(stub_names) == sorted(public_names)


def test_stub_matches_runtime_signatures():
    functions, _ = stub_contents()
    for function in functions:
        parameters = inspect.signature(getattr(emojet, function.name)).parameters
        args = function.args
        assert not args.posonlyargs
        assert args.vararg is None and args.kwarg is None

        positional = [
            parameter
            for parameter in parameters.values()
            if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        ]
        assert [parameter.name for parameter in positional] == [
            arg.arg for arg in args.args
        ]
        required_count = len(args.args) - len(args.defaults)
        for parameter in positional[:required_count]:
            assert parameter.default is inspect.Parameter.empty
        for parameter, default in zip(
            positional[required_count:], args.defaults, strict=True
        ):
            assert_default_matches(parameter, default)

        keyword_only = [
            parameter
            for parameter in parameters.values()
            if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        ]
        assert [parameter.name for parameter in keyword_only] == [
            arg.arg for arg in args.kwonlyargs
        ]
        for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            assert kw_default is not None
            assert_default_matches(parameters[arg.arg], kw_default)

        assert len(positional) + len(keyword_only) == len(parameters)


def test_stub_matches_documented_signatures():
    functions, _ = stub_contents()
    expected = {function.name: stub_signature(function) for function in functions}
    assert documented_signatures() == expected
