import ast
import sys
from pathlib import Path


def test_domain_has_no_framework_or_adapter_dependencies() -> None:
    root = Path(__file__).resolve().parents[2] / "backend" / "app"
    violations: list[str] = []
    for source in root.rglob("*.py"):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            imports = []
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, f"Use absolute imports: {source}"
                imports = [node.module or ""]
            for module in imports:
                if (
                    module.startswith("backend.app.")
                    or module.split(".")[0] in sys.stdlib_module_names
                ):
                    continue
                violations.append(f"{source.name}: {module}")
    assert not violations, violations
