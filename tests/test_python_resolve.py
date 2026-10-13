from conftest import call_targets, edge

from repolens.parsers.python_resolve import assign_module_names

# Module naming -----------------------------------------------------------------------


def ids(paths, root_name="repo"):
    return {path: name.id for path, name in assign_module_names(paths, root_name).items()}


def test_module_ids_follow_packages():
    assert ids(["src/shop/__init__.py", "src/shop/models.py", "setup.py"]) == {
        "src/shop/__init__.py": "shop",
        "src/shop/models.py": "shop.models",
        "setup.py": "setup",
    }


def test_namespace_folder_inside_a_package_keeps_the_package_prefix():
    assert (
        ids(["shop/__init__.py", "shop/sansio/app.py"])["shop/sansio/app.py"] == "shop.sansio.app"
    )


def test_scanning_a_package_folder_directly_uses_its_name():
    assert ids(["__init__.py", "core/__init__.py", "core/frame.py"], root_name="pandas") == {
        "__init__.py": "pandas",
        "core/__init__.py": "pandas.core",
        "core/frame.py": "pandas.core.frame",
    }


def test_colliding_scripts_fall_back_to_their_paths():
    assert ids(["scripts/run.py", "tools/run.py"]) == {
        "scripts/run.py": "scripts.run",
        "tools/run.py": "tools.run",
    }


# The sample project ------------------------------------------------------------------


def test_sample_nodes(sample_graph):
    nodes = sample_graph.nodes
    assert nodes["shop"].attrs["is_package"] is True
    assert nodes["shop.models:Order"].kind == "class"
    assert nodes["shop.models:Order"].docstring == "An order with line items."
    assert nodes["shop.models:Order.total"].kind == "method"
    assert nodes["shop.service:make_service"].signature == "() -> OrderService"
    assert nodes["file:README.md"].attrs["language"] == "markdown"
    assert nodes["dir:src/shop/utils"].kind == "directory"


def test_sample_imports(sample_graph):
    g = sample_graph
    assert edge(g, "imports", "shop.service", "shop.repo")  # relative import
    assert edge(g, "imports", "shop.service", "shop").attrs["names"] == ["Order"]
    assert edge(g, "imports", "report", "helpers")  # script importing its neighbour
    assert edge(g, "imports", "shop.utils.fmt", "shop.models").attrs["type_only"] is True
    assert g.nodes["ext:requests"].attrs == {"stdlib": False}
    assert g.nodes["ext:json"].attrs == {"stdlib": True}


def test_sample_inheritance_and_decorators(sample_graph):
    g = sample_graph
    assert edge(g, "inherits", "shop.models:Order", "shop.models:Base")
    assert edge(g, "decorates", "shop.utils.fmt:audited", "shop.service:OrderService.place")


def test_sample_calls(sample_graph):
    g = sample_graph
    assert call_targets(g, "shop.service:OrderService.place") == {
        "shop.models:Order": "resolved",  # re-exported through shop/__init__.py
        "shop.models:Order.total": "inferred",  # order = Order(); order.total()
        "shop.repo:OrderRepo.save": "inferred",  # self.repo typed by the __init__ annotation
        "shop.service:Carrier.dispatch_parcel": "guessed",  # untyped parameter, unique name
    }
    assert call_targets(g, "shop.cli:main") == {
        "shop.service:make_service": "resolved",
        "shop.service:OrderService.place": "inferred",  # via make_service's return annotation
        "shop.service:Carrier": "resolved",
        "shop.utils.fmt:money": "resolved",  # star import
    }
    assert call_targets(g, "shop.models:Order.total") == {"shop.models:Order._sum": "resolved"}
    assert call_targets(g, "shop.models:Order.empty") == {
        "shop.models:Order": "resolved",  # cls()
        "shop.models:Base.describe": "inferred",  # inherited method on cls() instance
    }
    assert call_targets(g, "shop.utils.fmt:order_label") == {
        "shop.models:Base.describe": "inferred"  # string annotation, TYPE_CHECKING import
    }
    assert call_targets(g, "report") == {"helpers:render": "resolved"}
    assert call_targets(g, "shop.cli") == {"shop.cli:main": "resolved"}


def test_sample_external_calls_and_entry_points(sample_graph):
    nodes = sample_graph.nodes
    assert nodes["shop.repo:OrderRepo.save"].attrs["external_calls"] == ["json.dumps"]
    assert nodes["shop.service:Carrier.dispatch_parcel"].attrs["external_calls"] == [
        "requests.post"
    ]
    assert nodes["shop.cli"].attrs["entry_point"] == "main-guard"
    assert nodes["shop.cli:main"].attrs["entry_point"] == "script:shop"
    assert "unresolved_calls" not in nodes["shop.models:Order._sum"].attrs  # list.append is builtin


def test_sample_syntax_error_does_not_stop_the_scan(sample_graph):
    assert sample_graph.nodes["shop.broken"].attrs["parse_error"].startswith("SyntaxError")
    assert sample_graph.stats()["parse_errors"] == 1


# Focused cases -----------------------------------------------------------------------


def test_super_and_external_base_classes(graph_of):
    g = graph_of(
        {
            "app.py": """
            import unittest

            class Base:
                def setup(self): ...

            class Child(Base):
                def setup(self):
                    super().setup()

            class MyTest(unittest.TestCase):
                def test_x(self):
                    self.assertEqual(1, 1)
            """
        }
    )
    assert call_targets(g, "app:Child.setup") == {"app:Base.setup": "resolved"}
    assert g.nodes["app:MyTest.test_x"].attrs["external_calls"] == ["unittest.TestCase.assertEqual"]


def test_module_variables_and_class_aliases(graph_of):
    g = graph_of(
        {
            "pkg/__init__.py": "",
            "pkg/registry.py": """
            import logging

            class Registry:
                def register(self, name): ...

            registry = Registry()
            log = logging.getLogger(__name__)
            """,
            "pkg/views.py": """
            from pkg.registry import registry, log, Registry

            class View:
                registry_class = Registry

                def build(self):
                    return self.registry_class()

            def setup():
                registry.register("x")
                log.info("ready")
            """,
        }
    )
    assert call_targets(g, "pkg.views:setup") == {"pkg.registry:Registry.register": "inferred"}
    assert g.nodes["pkg.views:setup"].attrs["external_calls"] == ["logging.getLogger.info"]
    assert call_targets(g, "pkg.views:View.build") == {"pkg.registry:Registry": "inferred"}


def test_local_type_shadows_module_variable(graph_of):
    g = graph_of(
        {
            "m.py": """
            class A:
                def go(self): ...

            class B:
                def go(self): ...

            thing = A()

            def f():
                thing = B()
                thing.go()
            """
        }
    )
    assert call_targets(g, "m:f") == {"m:B": "resolved", "m:B.go": "inferred"}


def test_stdlib_names_are_not_shadowed_by_package_modules(graph_of):
    g = graph_of(
        {
            "__init__.py": "",
            "typing.py": "",
            "app.py": "import typing as t\n\nX = t.TypeVar('X')\n",
        }
    )
    assert edge(g, "imports", f"{g.root_name}.app", "ext:typing")


def test_http_and_cli_entry_points(graph_of):
    g = graph_of(
        {
            "api.py": """
            app = FastAPI()

            @app.get("/items")
            def items(): ...

            @cli.command()
            def sync(): ...
            """
        }
    )
    assert g.nodes["api:items"].attrs["entry_point"] == "http"
    assert g.nodes["api:sync"].attrs["entry_point"] == "cli"


def test_inheritance_cycle_does_not_hang(graph_of):
    g = graph_of(
        {"m.py": "class A(B):\n    pass\n\nclass B(A):\n    def f(self):\n        self.g()\n"}
    )
    assert edge(g, "inherits", "m:A", "m:B") and edge(g, "inherits", "m:B", "m:A")
