import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend_api"))

from backend_api.main import app


schema = app.openapi()
targets = {}
for path, methods in schema.get("paths", {}).items():
    lower = path.lower()
    if not any(token in lower for token in [
        "container-reports", "vessel-grain-sampling", "vessel-truck-supervision",
        "draft-survey", "vessel-bunker-reports", "vessel-cargo-condition-surveys",
        "vessel-crane-inspection", "vessel-condition-surveys", "port-captancy-reports",
        "weight-certificates", "vessel-holds-inspection-certificates",
        "sampling-certificates", "sealing-certificates", "lashing-certificates",
        "logra-reports",
    ]):
        continue
    interesting = {}
    for method, spec in methods.items():
        if method.upper() in {"POST", "PUT", "GET", "DELETE"}:
            interesting[method.upper()] = {
                "operationId": spec.get("operationId"),
                "requestBody": spec.get("requestBody"),
                "parameters": spec.get("parameters"),
            }
    if interesting:
        targets[path] = interesting

out = Path("tmp") / "reports_request_schemas.json"
out.write_text(json.dumps({
    "paths": targets,
    "components": schema.get("components", {}).get("schemas", {}),
}, indent=2, default=str), encoding="utf-8")
print(out.resolve())

for path, methods in targets.items():
    print("\n", path)
    for method, spec in methods.items():
        body = spec.get("requestBody") or {}
        print(" ", method, spec.get("operationId"), "body=", bool(body))
        content = body.get("content") or {}
        for mime, item in content.items():
            print("   ", mime, item.get("schema"))
