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

import pslr

API_RST = Path(__file__).parent.parent / "docs" / "api.rst"
STUB_FILE = Path(__file__).parent.parent / "src" / "pslr" / "_lookup.pyi"


def stub_functions() -> list[ast.FunctionDef]:
    return [
        node
        for node in ast.parse(STUB_FILE.read_text()).body
        if isinstance(node, ast.FunctionDef)
    ]


def stub_data_names() -> list[str]:
    names = []
    for node in ast.parse(STUB_FILE.read_text()).body:
        if not isinstance(node, ast.FunctionDef):
            assert isinstance(node, ast.AnnAssign)
            assert isinstance(node.target, ast.Name)
            names.append(node.target.id)
    return names


def stub_signature(function: ast.FunctionDef) -> str:
    header = ast.unparse(function).splitlines()[0]
    signature = header.removeprefix("def ").removesuffix(":")
    # ast.unparse writes defaults as "=", the docs use PEP 8's " = "
    return signature.replace("=", " = ")


def documented_signatures() -> dict[str, str]:
    matches = re.finditer(
        r"^\.\. function:: ((\w+)\(.*)$",
        API_RST.read_text(),
        flags=re.MULTILINE,
    )
    return {match[2]: match[1] for match in matches}


def test_stub_matches_module_exports():
    stub_names = [function.name for function in stub_functions()] + stub_data_names()
    public_names = [
        name
        for name in dir(pslr)
        # Exclude the __future__ import that dir() picks up
        if not name.startswith("_") and name != "annotations"
    ]
    assert sorted(stub_names) == sorted(public_names)


def test_stub_matches_runtime_signatures():
    for function in stub_functions():
        parameters = inspect.signature(getattr(pslr, function.name)).parameters
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
        assert not args.defaults
        for parameter in positional:
            assert parameter.default is inspect.Parameter.empty

        keyword_only = [
            parameter
            for parameter in parameters.values()
            if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        ]
        assert [parameter.name for parameter in keyword_only] == [
            arg.arg for arg in args.kwonlyargs
        ]
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            assert default is not None
            assert parameters[arg.arg].default == ast.literal_eval(default)

        assert len(positional) + len(keyword_only) == len(parameters)


def test_stub_matches_documented_signatures():
    expected = {
        function.name: stub_signature(function) for function in stub_functions()
    }
    assert documented_signatures() == expected
