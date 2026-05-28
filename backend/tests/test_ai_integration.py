import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from backend.main import app
from backend.ai.core.ai_budget_manager import ai_budget_manager
from backend.ai.cache.ai_cache import ai_cache

@pytest.mark.asyncio
async def test_generate_strategy_plan_endpoint():
    """Verify that POST /api/ai/strategy-plan accepts parameter inputs, routes correctly, and returns structured plan."""
    
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True

    # We mock user verification by bypassing JWT check or patching it
    with patch("backend.auth.dependencies.get_current_user") as mock_user_dep, \
         patch.object(ai_budget_manager, "redis", mock_redis), \
         patch.object(ai_budget_manager, "connect", AsyncMock()), \
         patch.object(ai_cache, "redis", mock_redis), \
         patch.object(ai_cache, "connect", AsyncMock()), \
         patch("backend.ai.history.context_recall.ContextRecall.recall_similar_findings", new_callable=AsyncMock) as mock_recall:
         
        mock_recall.return_value = []
        
        mock_user = AsyncMock()
        mock_user.id = uuid4()
        mock_user.organization_id = uuid4()
        mock_user_dep.return_value = mock_user

        # Dynamically find the exact get_current_user function object registered on the strategy-plan route
        for route in app.routes:
            if "/strategy-plan" in route.path:
                for dep in route.dependant.dependencies:
                    if dep.call.__name__ == "get_current_user":
                        app.dependency_overrides[dep.call] = lambda: mock_user
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post(
            "/api/ai/strategy-plan",
            params={
                "org_id": str(mock_user.organization_id),
                "program_name": "Shopify Bounty Program",
                "tech_stack": "Ruby, Postgres"
            },
            json=["api.shopify.com", "admin.shopify.com"],
            headers={"Authorization": "Bearer fake_token"}
        )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["program"] == "Shopify Bounty Program"
        assert "strategic_plan" in data
        assert data["source"] == "ai_strategy_planner"

@pytest.mark.asyncio
async def test_budget_circuit_breaker():
    """Verify check_budget rejects routing when estimated token usage breaches default_hourly_limit."""
    mock_redis = AsyncMock()
    # Mock current usage to be near the limit (49,500 tokens used)
    mock_redis.get.return_value = "49500"
    
    with patch.object(ai_budget_manager, "redis", mock_redis), \
         patch.object(ai_budget_manager, "connect", AsyncMock()):
         
        # default limit is 50,000. Usage (49,500) + request (1,000) = 50,500 (breaches)
        is_ok = await ai_budget_manager.check_budget("org-uuid-123", 1000)
        assert is_ok is False
        
        # request under limit: Usage (49,500) + request (100) = 49,600 (within budget)
        is_ok_under = await ai_budget_manager.check_budget("org-uuid-123", 100)
        assert is_ok_under is True
