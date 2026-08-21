from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN = {("plan", "code"), ("subscription", "status")}
ROOT = Path("backend/apps")
violations: list[str] = []

for path in ROOT.rglob("*.py"):
    if "billing" in path.parts:
        continue
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if (node.value.id, node.attr) in FORBIDDEN:
                violations.append(f"{path}:{node.lineno}: {node.value.id}.{node.attr}")

if violations:
    raise SystemExit("Forbidden billing state access:\n" + "\n".join(violations))
print("Billing access gate passed: plan.code and subscription.status are billing-private.")
