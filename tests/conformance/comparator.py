from deepdiff import DeepDiff
from typing import Any, Dict, List, Optional
import re

def compare_responses(response_a: Any, response_b: Any, ignore_keys: Optional[List[str]] = None) -> DeepDiff:
    ignore_keys = set(ignore_keys) if ignore_keys else set()
    return DeepDiff(response_a, response_b, exclude_paths=[f"root['{k}']" for k in ignore_keys], ignore_order=True)

def normalize_graphql(response: Any) -> Any:
    if isinstance(response, dict):
        if "data" in response and len(response.keys()) == 1:
            return normalize_graphql(response["data"])
        for k, v in response.items():
            response[k] = normalize_graphql(v)
    elif isinstance(response, list):
        return [normalize_graphql(item) for item in response]
    return response

def normalize_casing(obj: Any, target: str = 'camel') -> Any:
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if target == 'camel':
                new_key = re.sub(r'_([a-z])', lambda m: m.group(1).upper(), k)
            else:
                new_key = re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), k)
            result[new_key] = normalize_casing(v, target)
        return result
    elif isinstance(obj, list):
        return [normalize_casing(item, target) for item in obj]
    return obj

def strip_volatile(obj: Any, keys=('id', 'createdAt', 'updatedAt', 'occurredAt', 'assignedAt')) -> Any:
    if isinstance(obj, dict):
        return {k: strip_volatile(v, keys) for k, v in obj.items() if k not in keys}
    elif isinstance(obj, list):
        return [strip_volatile(item, keys) for item in obj]
    return obj

def assert_structural_match(a: Any, b: Any) -> None:
    # Just compares types and keys
    diff = DeepDiff(a, b, ignore_order=True, exclude_types=[int, float, str, bool])
    assert not diff, format_diff_report(diff)

def assert_behavioral_match(a: Any, b: Any, ignore_keys: Optional[List[str]] = None) -> None:
    a_norm = strip_volatile(normalize_casing(normalize_graphql(a)))
    b_norm = strip_volatile(normalize_casing(normalize_graphql(b)))
    diff = compare_responses(a_norm, b_norm, ignore_keys)
    assert not diff, format_diff_report(diff)

def format_diff_report(diff: DeepDiff) -> str:
    return f"Differences found:\n{diff.pretty()}"
