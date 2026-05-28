import pytest
from unittest.mock import AsyncMock, patch
from backend.core.redis_lock import RedisLock

@pytest.mark.asyncio
async def test_redis_lock_acquire_success():
    """Verify that RedisLock acquires a lock successfully when the key doesn't exist."""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True # Successful nx write
    
    with patch("backend.core.redis_lock.get_redis", return_value=mock_redis):
        lock = RedisLock(key="test-endpoint", ttl_seconds=10)
        acquired = await lock.acquire(blocking=False)
        
        assert acquired is True
        mock_redis.set.assert_called_once_with("lock:test-endpoint", lock.token, px=10000, nx=True)

@pytest.mark.asyncio
async def test_redis_lock_acquire_collision():
    """Verify that RedisLock returns False on acquire collision (key already exists)."""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = False # Lock held
    
    with patch("backend.core.redis_lock.get_redis", return_value=mock_redis):
        lock = RedisLock(key="busy-endpoint", ttl_seconds=10)
        acquired = await lock.acquire(blocking=False)
        
        assert acquired is False
        mock_redis.set.assert_called_once()

@pytest.mark.asyncio
async def test_redis_lock_release_success():
    """Verify that releasing a lock executes eval (Lua script) to delete lock key atomic checks."""
    mock_redis = AsyncMock()
    mock_redis.eval.return_value = 1 # Deleted key
    
    with patch("backend.core.redis_lock.get_redis", return_value=mock_redis):
        lock = RedisLock(key="expiring-endpoint", ttl_seconds=10)
        # Seed lock redis association
        lock.redis = mock_redis
        
        await lock.release()
        mock_redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_replay_dlq_endpoint_success():
    """Verify that POST /api/scheduler/replay-dlq successfully replays jobs matching target org and removes them."""
    import json
    from uuid import uuid4
    from backend.main import app
    
    mock_redis = AsyncMock()
    # List has two jobs: one matching our org, one matching a different org
    matching_org_id = uuid4()
    other_org_id = uuid4()
    
    job_match = {
        "job_id": str(uuid4()),
        "organization_id": str(matching_org_id),
        "task_type": "recon_scan",
        "priority": "high",
        "attempts": 3
    }
    job_other = {
        "job_id": str(uuid4()),
        "organization_id": str(other_org_id),
        "task_type": "recon_scan",
        "priority": "low",
        "attempts": 3
    }
    
    mock_redis.lrange.return_value = [json.dumps(job_match), json.dumps(job_other)]
    mock_redis.lrem.return_value = 1 # Successfully removed
    
    mock_user = AsyncMock()
    mock_user.id = uuid4()
    
    with patch("backend.auth.dependencies.get_current_user", return_value=mock_user), \
         patch("backend.core.redis.get_redis", return_value=mock_redis), \
         patch("backend.queues.priority_queue.PriorityQueue.enqueue", new_callable=AsyncMock) as mock_enqueue, \
         patch("backend.core.permissions.RBACService.validate_workspace_access", new_callable=AsyncMock) as mock_val, \
         patch("backend.core.permissions.RBACService.check_permission", new_callable=AsyncMock) as mock_perm:
         
        # Override dependencies for test
        for route in app.routes:
            if "/replay-dlq" in route.path:
                for dep in route.dependant.dependencies:
                    if dep.call.__name__ == "get_current_user":
                        app.dependency_overrides[dep.call] = lambda: mock_user
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post(
            "/api/scheduler/replay-dlq",
            params={"organization_id": str(matching_org_id)},
            headers={"Authorization": "Bearer fake_token"}
        )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["replayed"] == 1
        
        # Verify validate_workspace_access and check_permission were called with proper args
        mock_val.assert_called_once_with(mock_user.id, matching_org_id)
        mock_perm.assert_called_once_with(mock_user.id, matching_org_id, "run_scans")
        
        # Verify lrem was called only for the matching job
        mock_redis.lrem.assert_called_once_with("cluster_jobs:dlq", count=1, value=json.dumps(job_match))
        # Verify matching job enqueued with attempts reset and queued status
        mock_enqueue.assert_called_once()
        queued_job_data = mock_enqueue.call_args[0][1]
        assert queued_job_data["attempts"] == 0
        assert queued_job_data["status"] == "queued"
        assert queued_job_data["organization_id"] == str(matching_org_id)


@pytest.mark.asyncio
async def test_replay_dlq_unauthorized():
    """Verify that POST /api/scheduler/replay-dlq returns 403 when user lacks workspace access."""
    from uuid import uuid4
    from backend.main import app
    
    mock_user = AsyncMock()
    mock_user.id = uuid4()
    org_id = uuid4()
    
    async def side_effect(user_id, organization_id):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )
        
    with patch("backend.auth.dependencies.get_current_user", return_value=mock_user), \
         patch("backend.core.permissions.RBACService.validate_workspace_access", side_effect=side_effect):
         
        for route in app.routes:
            if "/replay-dlq" in route.path:
                for dep in route.dependant.dependencies:
                    if dep.call.__name__ == "get_current_user":
                        app.dependency_overrides[dep.call] = lambda: mock_user
                        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post(
            "/api/scheduler/replay-dlq",
            params={"organization_id": str(org_id)},
            headers={"Authorization": "Bearer fake_token"}
        )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 403
        assert "You do not have access to this organization" in response.json()["detail"]

