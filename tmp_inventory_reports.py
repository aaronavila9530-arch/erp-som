import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend_api"))

from backend_api.main import app


schema = app.openapi()
paths = []
for path, methods in schema.get("paths", {}).items():
    if not any(token in path.lower() for token in [
        "report", "inform", "vessel", "draft", "sampling", "sealing",
        "lashing", "weight", "captancy", "bunker", "crane", "holds",
        "container", "logra"
    ]):
        continue
    item = {"path": path, "methods": {}}
    for method, spec in methods.items():
        item["methods"][method.upper()] = {
            "operationId": spec.get("operationId"),
            "tags": spec.get("tags"),
            "summary": spec.get("summary"),
            "requestBody": spec.get("requestBody"),
            "parameters": spec.get("parameters"),
        }
    paths.append(item)

out = Path("tmp") / "reports_openapi_inventory.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(paths, indent=2, default=str), encoding="utf-8")
print(out.resolve())
print("paths", len(paths))
for item in paths:
    methods = ",".join(item["methods"].keys())
    print(methods, item["path"])
