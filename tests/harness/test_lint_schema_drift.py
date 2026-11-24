from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import lint_schema_drift as lsd


def test_normalize_path():
    assert lsd.normalize_path("/api/lots/{lotNumber}/traceability/") == "/lots/{param}/traceability"
    assert lsd.normalize_path("/api/compliance/ledger") == "/compliance/ledger"
    assert lsd.normalize_path("compliance/verify") == "/compliance/verify"
    assert lsd.normalize_path("/api") == "/"


def test_validate_openapi_refs_detects_dangling_refs():
    valid_spec = {
        "components": {
            "schemas": {
                "Item": {"type": "object"},
                "Order": {"type": "object", "properties": {"item": {"$ref": "#/components/schemas/Item"}}},
            }
        }
    }
    assert lsd.validate_openapi_refs(valid_spec, "VALID") == []

    broken_spec = {
        "components": {
            "schemas": {
                "Order": {"type": "object", "properties": {"item": {"$ref": "#/components/schemas/MissingType"}}},
            }
        }
    }
    errs = lsd.validate_openapi_refs(broken_spec, "BROKEN")
    assert len(errs) == 1
    assert "MissingType" in errs[0]


def test_check_openapi_equivalence_catches_method_and_property_drift():
    base = {
        "paths": {"/api/items": {"get": {"responses": {"200": {"description": "OK"}}}}},
        "components": {"schemas": {"Item": {"type": "object", "properties": {"id": {"type": "string"}}}}},
    }
    assert lsd.check_openapi_equivalence(base, base) == 0

    method_drift = {
        "paths": {"/api/items": {"post": {"responses": {"200": {"description": "OK"}}}}},
        "components": {"schemas": {"Item": {"type": "object", "properties": {"id": {"type": "string"}}}}},
    }
    assert lsd.check_openapi_equivalence(base, method_drift) >= 1

    prop_drift = {
        "paths": {"/api/items": {"get": {"responses": {"200": {"description": "OK"}}}}},
        "components": {"schemas": {"Item": {"type": "object", "properties": {"sku": {"type": "string"}}}}},
    }
    assert lsd.check_openapi_equivalence(base, prop_drift) >= 1


def test_extract_python_fastapi_routes_and_live_parity(tmp_path):
    sample = tmp_path / "sample_router.py"
    sample.write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter(prefix='/api/v1')\n"
        "@router.get('/items/{item_id}')\n"
        "async def get_item(item_id: str):\n"
        "    return {}\n",
        encoding="utf-8",
    )
    discovered = lsd.extract_python_fastapi_routes(str(tmp_path))
    assert ("get", "/v1/items/{param}") in discovered

    # Live check against python-ddd-inventory/src/presentation
    py_pres = ROOT / "python-ddd-inventory" / "src" / "presentation"
    assert lsd.check_python_route_parity(str(py_pres)) == 0

    # Negative check when a required route is missing
    assert lsd.check_python_route_parity(str(tmp_path), required_routes={("post", "/nonexistent")}) == 1


def test_check_graphql_coverage_and_client_coverage():
    openapi = {"components": {"schemas": {"Product": {}, "JournalEntry": {}}}, "paths": {"/api/products": {}}}
    valid_gql = """
    type Product @key(fields: "id") { id: ID! }
    type ProductVariant @key(fields: "id") { sku: String! }
    type JournalEntry { id: ID! }
    type SerializedItem { serialNumber: String! }
    type InventoryItem { quantity: Int! }
    """
    assert lsd.check_graphql_coverage(valid_gql, openapi) == 0
    assert lsd.check_graphql_coverage("type OnlyOne { id: ID! }", openapi) == 1

    valid_client = "export interface InventoryClient { getProducts(): Promise<void>; }"
    assert lsd.check_client_coverage(valid_client, openapi) == 0
    assert lsd.check_client_coverage("export const x = 1;", openapi) == 1
