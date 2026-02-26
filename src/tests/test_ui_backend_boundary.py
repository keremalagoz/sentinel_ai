from pathlib import Path
import re


FORBIDDEN_PATTERNS = [
    re.compile(r"^\s*from\s+src\.(ai|core)\.", re.MULTILINE),
    re.compile(r"^\s*import\s+src\.(ai|core)(\.|\s|$)", re.MULTILINE),
]


ALLOWED_FILES = {
    "__init__.py",
}


def test_ui_does_not_import_ai_core_directly():
    ui_dir = Path(__file__).resolve().parents[1] / "ui"
    violations = []

    for py_file in ui_dir.glob("*.py"):
        if py_file.name in ALLOWED_FILES:
            continue

        content = py_file.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(content):
                violations.append(str(py_file))
                break

    assert not violations, (
        "UI katmanı doğrudan src.ai/src.core import etmemeli. "
        f"Gateway kullanın. Violations: {violations}"
    )
