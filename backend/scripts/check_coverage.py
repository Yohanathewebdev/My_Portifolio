import json
from pathlib import Path

data = json.loads(Path("coverage.json").read_text())
files = data["files"]
required = {
    "backend/apps/core/scoping.py": 100.0,
    "backend/apps/core/exceptions.py": 100.0,
}
failures = []
for path, minimum in required.items():
    summary = files.get(path, {}).get("summary", {})
    percent = summary.get("percent_covered", 0)
    if percent < minimum:
        failures.append(f"{path}: {percent:.2f}% < {minimum:.2f}%")
if failures:
    raise SystemExit("Coverage requirements failed:\n" + "\n".join(failures))
print("Targeted coverage gate passed: scoping and exception handler are 100%.")
