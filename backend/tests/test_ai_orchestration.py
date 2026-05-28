import pytest
from backend.ai.core.prompt_optimizer import prompt_optimizer
from backend.ai.core.ai_budget_manager import ai_budget_manager
from backend.ai.router.provider_router import provider_router

def test_prompt_compression():
    """Verify that prompt_optimizer trims boilerplate filler to reduce input token usage."""
    raw_prompt = "please analyze the following SQL vulnerability and could you write a report on the details"
    compressed = prompt_optimizer.compress_prompt(raw_prompt)
    
    assert "please analyze the following" not in compressed
    assert "Analyze:" in compressed

@pytest.mark.asyncio
async def test_strict_anthropic_violation():
    """Verify that provider_router strictly rejects direct Anthropic/Claude execution to maintain Gemini enforcement."""
    messages = [{"role": "user", "content": "Test prompt"}]
    
    with pytest.raises(ValueError) as exc:
        await provider_router.route_request(messages, "claude-sonnet-v1")
        
    assert "Direct Anthropic API usage is STRICTLY PROHIBITED" in str(exc.value)

@pytest.mark.asyncio
async def test_strategy_planning_verdict():
    """Verify that ai_strategy_planner correctly plans prioritized hunts."""
    from unittest.mock import AsyncMock, patch
    from backend.ai.core.ai_strategy_planner import ai_strategy_planner
    from backend.ai.core.ai_budget_manager import ai_budget_manager
    from backend.ai.cache.ai_cache import ai_cache
    
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    
    with patch.object(ai_budget_manager, "redis", mock_redis), \
         patch.object(ai_budget_manager, "connect", AsyncMock()), \
         patch.object(ai_cache, "redis", mock_redis), \
         patch.object(ai_cache, "connect", AsyncMock()):
         
        res = await ai_strategy_planner.generate_hunt_plan(
            org_id="system",
            program_name="Test Program",
            tech_stack="FastAPI, React, Redis",
            live_endpoints=["/api/v1/users", "/api/v1/auth"]
        )
        assert res["program"] == "Test Program"
        assert "strategic_plan" in res


