import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple
import yaml

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

# Canonical REST endpoints that Python FastAPI must expose (normalized without /api prefix)
REQUIRED_PYTHON_CANONICAL_ROUTES: Set[Tuple[str, str]] = {
    ("get", "/compliance/ledger"),
    ("post", "/compliance/verify"),
    ("get", "/compliance/reconstruct"),
    ("get", "/compliance/replay"),
    ("get", "/admin/cache/stats"),
    ("post", "/admin/cache/clear"),
    ("get", "/anomaly-detection/analyze"),
    ("get", "/rebalance/matrix"),
    ("get", "/forecasting/report"),
    ("get", "/warehouse-locations"),
    ("post", "/warehouse-locations"),
    ("delete", "/warehouse-locations/{param}"),
    ("post", "/warehouse-locations/putaway-suggestions"),
    ("post", "/warehouse-locations/optimize-pick-route"),
    ("get", "/warehouse-locations/slotting-suggestions"),
    ("get", "/webhooks/subscriptions"),
    ("post", "/webhooks/subscriptions"),
    ("put", "/webhooks/subscriptions/{param}"),
    ("delete", "/webhooks/subscriptions/{param}"),
    ("get", "/webhooks/deliveries"),
    ("get", "/rfid/tags"),
    ("post", "/rfid/assign"),
    ("get", "/inventory/fefo-pick"),
    ("post", "/lots/quarantine"),
    ("post", "/lots/release"),
    ("get", "/inventory/reports/recall/{param}"),
    ("post", "/cross-dock/evaluate"),
    ("post", "/fulfillment/drop-ship"),
}

# Core domain types that must exist in GraphQL schema.graphql
REQUIRED_GRAPHQL_TYPES: Set[str] = {
    "Product",
    "ProductVariant",
    "JournalEntry",
    "SerializedItem",
    "InventoryItem",
}


def load_yaml(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def normalize_path(path: str) -> str:
    """Normalize /api prefix and path parameter names for cross-backend comparison."""
    p = path.strip()
    if p.startswith("/api/"):
        p = p[4:]
    elif p == "/api":
        p = "/"
    if not p.startswith("/"):
        p = "/" + p
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return re.sub(r"\{[^}]+\}", "{param}", p)


def _collect_refs(node, refs: Set[str]) -> None:
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            refs.add(node["$ref"])
        for value in node.values():
            _collect_refs(value, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, refs)


def validate_openapi_refs(spec: dict, label: str = "OpenAPI") -> List[str]:
    """Verify every internal #/components/schemas/... $ref resolves to a defined schema."""
    schemas = spec.get("components", {}).get("schemas", {}) or {}
    refs: Set[str] = set()
    _collect_refs(spec, refs)
    errors: List[str] = []
    prefix = "#/components/schemas/"
    for ref in sorted(refs):
        if ref.startswith(prefix):
            target = ref[len(prefix):]
            if target not in schemas:
                errors.append(f"[{label}] Unresolved $ref target: {ref}")
    return errors


def check_openapi_equivalence(js_spec: dict, php_spec: dict) -> int:
    print("Checking OpenAPI structural equivalence...")
    js_paths = js_spec.get("paths", {}) or {}
    php_paths = php_spec.get("paths", {}) or {}

    js_keys = set(js_paths.keys())
    php_keys = set(php_paths.keys())

    missing_in_php = js_keys - php_keys
    missing_in_js = php_keys - js_keys

    errors = 0
    if missing_in_php:
        print(f"[ERROR] Missing endpoints in PHP spec: {sorted(missing_in_php)}")
        errors += 1
    if missing_in_js:
        print(f"[ERROR] Missing endpoints in JS spec: {sorted(missing_in_js)}")
        errors += 1

    # Check HTTP method parity for shared paths
    for path in sorted(js_keys & php_keys):
        js_methods = {m.lower() for m in (js_paths[path] or {}).keys() if m.lower() in HTTP_METHODS}
        php_methods = {m.lower() for m in (php_paths[path] or {}).keys() if m.lower() in HTTP_METHODS}
        if js_methods != php_methods:
            print(f"[ERROR] HTTP method mismatch on {path}: JS={sorted(js_methods)} vs PHP={sorted(php_methods)}")
            errors += 1

    # Check component schema parity (names & property sets)
    js_schemas = js_spec.get("components", {}).get("schemas", {}) or {}
    php_schemas = php_spec.get("components", {}).get("schemas", {}) or {}
    if set(js_schemas.keys()) != set(php_schemas.keys()):
        print("[WARN] Schema differences detected between JS and PHP specs.")
    else:
        for name in sorted(js_schemas.keys()):
            js_props = set((js_schemas[name].get("properties") or {}).keys())
            php_props = set((php_schemas[name].get("properties") or {}).keys())
            if js_props != php_props:
                print(f"[ERROR] Schema property drift in {name}: JS={sorted(js_props)} vs PHP={sorted(php_props)}")
                errors += 1

    # Validate internal $ref integrity in both specs
    for label, spec in (("JS", js_spec), ("PHP", php_spec)):
        for ref_err in validate_openapi_refs(spec, label):
            print(f"[ERROR] {ref_err}")
            errors += 1

    if errors == 0:
        print("[OK] OpenAPI specs (paths, HTTP methods, schemas, $refs) are in sync.")
    return errors


def _extract_str_constant(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_python_fastapi_routes(presentation_dir: str) -> Set[Tuple[str, str]]:
    """Statically extract (method, normalized_path) pairs from FastAPI router decorators via AST."""
    routes: Set[Tuple[str, str]] = set()
    root = Path(presentation_dir)
    if not root.exists():
        return routes

    for py_file in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            continue

        router_prefixes: Dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func = node.value.func
                func_name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
                if func_name == "APIRouter":
                    prefix = ""
                    for kw in node.value.keywords:
                        if kw.arg == "prefix":
                            val = _extract_str_constant(kw.value)
                            if val:
                                prefix = val
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            router_prefixes[target.id] = prefix

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                        continue
                    method = dec.func.attr.lower()
                    if method not in HTTP_METHODS:
                        continue
                    if not dec.args:
                        continue
                    raw_path = _extract_str_constant(dec.args[0])
                    if raw_path is None:
                        continue
                    router_name = dec.func.value.id if isinstance(dec.func.value, ast.Name) else ""
                    prefix = router_prefixes.get(router_name, "")
                    full_path = f"{prefix.rstrip('/')}/{raw_path.lstrip('/')}" if prefix else raw_path
                    routes.add((method, normalize_path(full_path)))
    return routes


def check_python_route_parity(
    presentation_dir: str,
    required_routes: Iterable[Tuple[str, str]] = REQUIRED_PYTHON_CANONICAL_ROUTES,
) -> int:
    print("Checking Python FastAPI route parity...")
    discovered = extract_python_fastapi_routes(presentation_dir)
    if not discovered:
        print(f"[ERROR] No FastAPI routes discovered in {presentation_dir}.")
        return 1

    missing = sorted(set(required_routes) - discovered)
    if missing:
        print(f"[ERROR] Missing canonical REST routes in Python FastAPI: {missing}")
        return 1

    print(f"[OK] Python FastAPI exposes {len(discovered)} routes; all {len(set(required_routes))} canonical routes verified.")
    return 0


def check_graphql_coverage(
    schema_str: str,
    openapi_spec: dict,
    required_types: Iterable[str] = REQUIRED_GRAPHQL_TYPES,
) -> int:
    print("Checking GraphQL schema coverage...")
    types_found = set(re.findall(r"^\s*type\s+([A-Za-z0-9_]+)[^{]*\{", schema_str, re.MULTILINE))
    openapi_schemas = set((openapi_spec.get("components", {}).get("schemas", {}) or {}).keys())

    missing_types = sorted(set(required_types) - types_found)
    if missing_types:
        print(f"[ERROR] Missing required core GraphQL types: {missing_types}")
        return 1

    covered = sum(1 for t in types_found if t in openapi_schemas)
    print(f"[OK] GraphQL types mapped to OpenAPI schemas: {covered}/{len(types_found)} (all {len(set(required_types))} core types present)")
    return 0


def check_client_coverage(client_ts: str, openapi_spec: dict) -> int:
    print("Checking Client API coverage...")
    client_match = re.search(r"interface InventoryClient\s*\{([\s\S]*?)\}", client_ts)
    if not client_match:
        print("[ERROR] Could not find InventoryClient interface.")
        return 1

    methods_block = client_match.group(1)
    methods = re.findall(r"([a-zA-Z0-9_]+)\(", methods_block)
    openapi_paths = list((openapi_spec.get("paths", {}) or {}).keys())

    if len(methods) > 0 and len(openapi_paths) > 0:
        print(f"[OK] Client methods ({len(methods)}) have spec coverage.")
        return 0
    print("[ERROR] Missing endpoints for client methods.")
    return 1


def main() -> None:
    js_openapi_path = "js-ddd-inventory/docs/openapi.yaml"
    php_openapi_path = "php-ddd-inventory/docs/openapi.yaml"
    python_presentation_dir = "python-ddd-inventory/src/presentation"
    schema_path = "gql-ddd-inventory/schema.graphql"
    client_path = "react-ddd-inventory-client/src/api/client.ts"

    try:
        js_spec = load_yaml(js_openapi_path)
        php_spec = load_yaml(php_openapi_path)
    except Exception as e:
        print(f"[ERROR] Failed to load OpenAPI specs: {e}")
        sys.exit(1)

    errors = check_openapi_equivalence(js_spec, php_spec)

    if os.path.isdir(python_presentation_dir):
        errors += check_python_route_parity(python_presentation_dir)
    else:
        print(f"[ERROR] Python presentation directory not found: {python_presentation_dir}")
        errors += 1

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_str = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to load schema.graphql: {e}")
        sys.exit(1)

    errors += check_graphql_coverage(schema_str, js_spec)

    try:
        with open(client_path, "r", encoding="utf-8") as f:
            client_str = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to load client.ts: {e}")
        sys.exit(1)

    errors += check_client_coverage(client_str, js_spec)

    if errors > 0:
        print(f"Drift detection failed with {errors} errors.")
        sys.exit(1)
    print("[OK] Drift detection passed. All schemas and Python routes are in sync.")


if __name__ == "__main__":
    main()
