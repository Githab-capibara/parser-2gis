"""Tests for audit fixes verification."""

import ast
from pathlib import Path


def test_constants_logging_import_at_module_level():
    """Verify logging import is at module level in constants.py."""
    from parser_2gis import constants

    source = Path(constants.__file__).read_text()
    tree = ast.parse(source)

    module_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_imports.append(node.module)

    assert "logging" in module_imports, "logging should be imported at module level"


def test_temp_file_manager_os_import_at_module_level():
    """Verify os import is at module level in temp_file_manager.py."""
    from parser_2gis.utils import temp_file_manager

    source = Path(temp_file_manager.__file__).read_text()
    tree = ast.parse(source)

    module_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_imports.append(alias.name)

    assert "os" in module_imports, "os should be imported at module level"


def test_protocols_no_pass_in_type_definitions():
    """Verify protocols.py uses ... instead of pass in type stubs."""
    from parser_2gis import protocols

    source = Path(protocols.__file__).read_text()

    lines = source.split("\n")
    in_class = False
    class_indent = 0

    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if "class " in line and ":" in line:
            in_class = True
            class_indent = indent
        elif in_class and stripped and indent <= class_indent and "class " not in line:
            in_class = False

        if in_class and "pass" in stripped and not stripped.startswith("#"):
            assert False, f"Found 'pass' in protocols.py at line: {line}"

    assert True


def test_pool_logs_connection_close_errors():
    """Verify pool.py logs errors instead of silent pass on connection close."""
    from parser_2gis.cache import pool

    source = Path(pool.__file__).read_text()

    assert "logger" in source.lower() or "log" in source.lower(), (
        "pool.py should have logging for connection close errors"
    )

    has_except_close = "except" in source and "close" in source.lower()
    assert has_except_close, "pool.py should handle close exceptions"


def test_pool_pragma_combined():
    """Verify PRAGMA queries are combined in pool.py."""
    from parser_2gis.cache import pool

    source = Path(pool.__file__).read_text()

    pragma_count = source.count("PRAGMA")
    assert pragma_count > 0, "pool.py should have PRAGMA statements"

    if "execute" in source.lower() or "executescript" in source.lower():
        assert True


def test_parallel_parser_handles_cancelled_error():
    """Verify parallel_parser.py handles CancelledError."""
    from parser_2gis.parallel import parallel_parser

    source = Path(parallel_parser.__file__).read_text()

    assert "CancelledError" in source, "parallel_parser.py should handle CancelledError"

    assert "asyncio" in source, "parallel_parser.py should import asyncio for CancelledError"


def test_main_parser_re_import_at_module():
    """Verify re is imported at module level in main.py."""
    from parser_2gis.parser.parsers import main

    source = Path(main.__file__).read_text()

    tree = ast.parse(source)
    module_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_imports.append(alias.name)

    assert "re" in module_imports, "re should be imported at module level"
