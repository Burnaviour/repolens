import ast
import sys
import textwrap

import pytest

from repolens.parsers.python_ast import annotation_parts, extract_module, read_source


def extract(source: str):
    return extract_module("m.py", textwrap.dedent(source))


def annotation(text: str):
    return annotation_parts(ast.parse(text, mode="eval").body)


def test_definitions_signatures_and_docstrings():
    info = extract(
        '''
        """Module doc."""

        class A(Base, metaclass=Meta):
            """Class doc."""

            @staticmethod
            def s(x: int = 1, *args, **kw) -> str:
                """Static doc."""

            async def m(self):
                def inner():
                    pass
        '''
    )
    assert info.docstring == "Module doc."
    assert info.classes["A"].bases == ["Base"]
    assert info.classes["A"].docstring == "Class doc."
    s = info.functions["A.s"]
    assert s.is_method and s.self_name is None
    assert s.signature == "(x: int=1, *args, **kw) -> str"
    assert s.annotated == {"x": ("int",), "args": ("tuple",), "kw": ("dict",)}
    m = info.functions["A.m"]
    assert m.is_async and m.self_name == "self"
    assert m.children == ["A.m.inner"]
    assert not info.functions["A.m.inner"].is_method


def test_calls_are_attributed_to_the_innermost_scope():
    info = extract(
        """
        setup()

        @register("x")
        def f(cb=default_cb()):
            helper()
            obj.method().chain()
            items = [transform(i) for i in data]
            super().save()
            fn = lambda: inside_lambda()

        if __name__ == "__main__":
            f()
        """
    )
    module_calls = {c.parts for c in info.calls}
    assert module_calls == {("setup",), ("register",), ("default_cb",), ("f",)}
    f_calls = {c.parts for c in info.functions["f"].calls}
    assert f_calls == {
        ("helper",),
        ("obj", "method"),
        ("transform",),
        ("super()", "save"),
        ("inside_lambda",),
    }
    assert info.has_main_guard


def test_imports_and_type_checking():
    info = extract(
        """
        import os.path
        import numpy as np
        from . import sibling
        from ..pkg.mod import Thing as T, other
        from x import *
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from heavy import Model

        def f():
            import json
        """
    )
    rows = [(b.local, b.module, b.level, b.name, b.type_only) for b in info.imports]
    assert rows == [
        ("os", "os.path", 0, None, False),
        ("np", "numpy", 0, None, False),
        ("sibling", "", 1, "sibling", False),
        ("T", "pkg.mod", 2, "Thing", False),
        ("other", "pkg.mod", 2, "other", False),
        (None, "x", 0, "*", False),
        ("TYPE_CHECKING", "typing", 0, "TYPE_CHECKING", False),
        ("Model", "heavy", 0, "Model", True),
    ]
    assert [b.module for b in info.functions["f"].imports] == ["json"]


def test_assignment_types():
    info = extract(
        """
        registry = Registry()
        names: list[str] = []

        class Service:
            repo_class = Repo
            cache: Cache

            def __init__(self, repo: Repo, client):
                self.repo = repo
                self.client = Client()
                self.items = []
                self.hinted: Thing = make()
        """
    )
    assert info.assigned_from_call == {"registry": ("Registry",)}
    assert info.annotated["names"] == ("list",)
    service = info.classes["Service"]
    assert service.attr_alias == {"repo_class": ("Repo",)}
    assert service.attr_types == {"cache": ("Cache",), "items": ("list",), "hinted": ("Thing",)}
    assert service.attr_from_param == {"repo": ("Repo",)}
    assert service.attr_from_call == {"client": ("Client",)}


def test_annotation_parts():
    assert annotation("Order") == ("Order",)
    assert annotation("models.Order") == ("models", "Order")
    assert annotation("'Order'") == ("Order",)
    assert annotation("Optional[Order]") == ("Order",)
    assert annotation("Order | None") == ("Order",)
    assert annotation("Annotated[Order, 'meta']") == ("Order",)
    assert annotation("list[Order]") == ("list",)
    assert annotation("Union[A, B]") is None
    assert annotation("A | B") is None


def test_syntax_error_is_recorded():
    info = extract("def broken(:\n")
    assert info.error and info.error.startswith("SyntaxError")
    assert info.functions == {}


def test_read_source_honours_coding_cookie():
    data = "# -*- coding: latin-1 -*-\nname = 'café'\n".encode("latin-1")
    assert "café" in read_source(data)


def test_python_314_unparenthesized_except_is_accepted():
    info = extract(
        """
        def load():
            try:
                fetch()
            except ValueError, KeyError:
                retry()
        """
    )
    assert info.error is None
    assert {c.parts for c in info.functions["load"].calls} == {("fetch",), ("retry",)}


@pytest.mark.skipif(sys.version_info < (3, 11), reason="except* needs Python 3.11")
def test_python_314_unparenthesized_except_star_is_accepted():
    info = extract(
        """
        def load():
            try:
                fetch()
            except* OSError, TimeoutError:
                give_up()
        """
    )
    assert info.error is None
    assert {c.parts for c in info.functions["load"].calls} == {("fetch",), ("give_up",)}
