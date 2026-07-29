# Conformance Test Suite

This suite verifies that the GraphQL, Express REST, and PHP REST backends all exhibit identical behavior and conform to the canonical interfaces.

## Setup
1. `pip install -r requirements.txt`
2. Ensure all 3 backends are running on ports 4000, 5000, and 8000 respectively.
3. Run `pytest` from this directory.

## Structure
- `conftest.py`: Fixtures for connecting to each backend
- `comparator.py`: Deep comparison utilities for normalizing responses (stripping volatile fields, normalizing casing)
- `canonical_types.yaml`: Canonical types schema
- `test_*.py`: Test modules covering different domain areas
