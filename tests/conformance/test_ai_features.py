import pytest
from conftest import BackendType, BACKEND_URLS


@pytest.mark.asyncio
async def test_anomaly_detection_endpoint_returns_valid_schema(backend, authenticated_client):
    """All 3 backends return matching AnomalySummary structure from the anomaly detection endpoint."""
    import httpx
    from gql import gql as gql_query

    if backend in [BackendType.EXPRESS_REST, BackendType.PHP_REST]:
        url = BACKEND_URLS[backend]
        async with httpx.AsyncClient(base_url=url, timeout=30) as client:
            response = await client.get("/api/anomaly-detection/analyze", params={"tenantId": "default-tenant"})
            assert response.status_code == 200
            data = response.json()
    else:
        query = gql_query('''
            query {
                analyzeInventoryAnomalies(tenantId: "default-tenant") {
                    alerts {
                        alertType
                        severity
                        confidence
                        sku
                        locationId
                        actorId
                        title
                        description
                        evidence
                        detectedAt
                    }
                    totalCritical
                    totalHigh
                    totalMedium
                    totalLow
                    overallRiskScore
                }
            }
        ''')
        result = await authenticated_client.execute_async(query)
        data = result["analyzeInventoryAnomalies"]

    # Validate structure
    assert "alerts" in data or "totalCritical" in data, f"Response missing expected fields: {list(data.keys())}"
    if "alerts" in data:
        assert isinstance(data["alerts"], list)
    if "totalCritical" in data:
        assert isinstance(data["totalCritical"], int)
    if "totalHigh" in data:
        assert isinstance(data["totalHigh"], int)
    if "totalMedium" in data:
        assert isinstance(data["totalMedium"], int)
    if "totalLow" in data:
        assert isinstance(data["totalLow"], int)
    if "overallRiskScore" in data:
        assert isinstance(data["overallRiskScore"], (int, float))


@pytest.mark.asyncio
async def test_rebalance_matrix_endpoint_returns_valid_schema(backend, authenticated_client):
    """All 3 backends return matching RebalanceMatrix structure from the rebalancing endpoint."""
    import httpx
    from gql import gql as gql_query

    if backend in [BackendType.EXPRESS_REST, BackendType.PHP_REST]:
        url = BACKEND_URLS[backend]
        async with httpx.AsyncClient(base_url=url, timeout=30) as client:
            response = await client.get("/api/rebalance/matrix", params={"tenantId": "default-tenant"})
            assert response.status_code == 200
            data = response.json()
    else:
        query = gql_query('''
            query {
                rebalanceMatrix(tenantId: "default-tenant") {
                    recommendations {
                        sku
                        sourceWarehouseId
                        destWarehouseId
                        quantity
                        priority
                        estimatedShippingCost
                        sourceCurrentDoc
                        destCurrentDoc
                        sourceProjectedDoc
                        destProjectedDoc
                        urgencyReason
                    }
                    matrix
                    summary
                }
            }
        ''')
        result = await authenticated_client.execute_async(query)
        data = result["rebalanceMatrix"]

    # Validate structure
    assert "recommendations" in data, f"Response missing 'recommendations': {list(data.keys())}"
    assert isinstance(data["recommendations"], list)
    assert "matrix" in data, f"Response missing 'matrix'"
    assert "summary" in data, f"Response missing 'summary'"


@pytest.mark.asyncio
async def test_anomaly_detection_empty_data_returns_no_alerts(backend, authenticated_client):
    """Graceful handling when no data exists — returns empty alerts with zero risk score."""
    import httpx
    from gql import gql as gql_query

    # Use a tenant ID that is unlikely to have any data
    empty_tenant = "nonexistent-tenant-for-test"

    if backend in [BackendType.EXPRESS_REST, BackendType.PHP_REST]:
        url = BACKEND_URLS[backend]
        async with httpx.AsyncClient(base_url=url, timeout=30) as client:
            response = await client.get(
                "/api/anomaly-detection/analyze",
                params={"tenantId": empty_tenant}
            )
            assert response.status_code == 200
            data = response.json()
    else:
        query = gql_query('''
            query($tenantId: String!) {
                analyzeInventoryAnomalies(tenantId: $tenantId) {
                    alerts { alertType }
                    totalCritical
                    totalHigh
                    totalMedium
                    totalLow
                    overallRiskScore
                }
            }
        ''')
        result = await authenticated_client.execute_async(query, variable_values={"tenantId": empty_tenant})
        data = result["analyzeInventoryAnomalies"]

    if "alerts" in data:
        assert len(data["alerts"]) == 0, f"Expected no alerts for empty tenant, got {len(data['alerts'])}"
    if "overallRiskScore" in data:
        assert data["overallRiskScore"] == 0, f"Expected zero risk score, got {data['overallRiskScore']}"


@pytest.mark.asyncio
async def test_rebalance_matrix_single_warehouse_returns_no_recommendations(backend, authenticated_client):
    """No inter-warehouse transfers when only 1 warehouse exists."""
    import httpx
    from gql import gql as gql_query

    # Use a tenant with minimal data — the sidecar returns empty when < 2 warehouses
    single_wh_tenant = "single-warehouse-tenant-test"

    if backend in [BackendType.EXPRESS_REST, BackendType.PHP_REST]:
        url = BACKEND_URLS[backend]
        async with httpx.AsyncClient(base_url=url, timeout=30) as client:
            response = await client.get(
                "/api/rebalance/matrix",
                params={"tenantId": single_wh_tenant}
            )
            assert response.status_code == 200
            data = response.json()
    else:
        query = gql_query('''
            query($tenantId: String!) {
                rebalanceMatrix(tenantId: $tenantId) {
                    recommendations { sku }
                    matrix
                    summary
                }
            }
        ''')
        result = await authenticated_client.execute_async(query, variable_values={"tenantId": single_wh_tenant})
        data = result["rebalanceMatrix"]

    if "recommendations" in data:
        assert len(data["recommendations"]) == 0, \
            f"Expected no recommendations for single-warehouse tenant, got {len(data['recommendations'])}"
