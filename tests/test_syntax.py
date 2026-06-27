import ast
import os
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "src")


def _iter_py_files():
    for root, _dirs, files in os.walk(ROOT):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


@pytest.mark.parametrize("path", list(_iter_py_files()))
def test_python_syntax(path):
    with open(path, encoding="utf-8") as f:
        ast.parse(f.read())
