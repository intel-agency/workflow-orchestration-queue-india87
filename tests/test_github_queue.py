"""Tests for the github_queue module."""

import pytest
import respx
import httpx

from src.models.work_item import TaskType, WorkItemStatus, WorkItem
from src.queue.github_queue import ITaskQueue, GitHubQueue


class TestITaskQueue:
    """Tests for ITaskQueue abstract interface."""

    def test_cannot_instantiate_directly(self):
        """Verify ITaskQueue cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ITaskQueue()


class TestGitHubQueue:
    """Tests for GitHubQueue implementation."""

    @pytest.fixture
    def queue(self):
        """Create a GitHubQueue instance for testing."""
        return GitHubQueue(token="test-token", org="test-org", repo="test-repo")

    @pytest.fixture
    def sample_work_item(self):
        """Create a sample WorkItem for testing."""
        return WorkItem(
            id="12345",
            issue_number=42,
            source_url="https://github.com/test-org/test-repo/issues/42",
            context_body="Test issue body",
            target_repo_slug="test-org/test-repo",
            task_type=TaskType.IMPLEMENT,
            status=WorkItemStatus.QUEUED,
            node_id="node_123",
        )

    def test_queue_initialization(self, queue):
        """Verify GitHubQueue initializes correctly."""
        assert queue.token == "test-token"
        assert queue.org == "test-org"
        assert queue.repo == "test-repo"
        assert "Authorization" in queue.headers
        assert queue.headers["Authorization"] == "token test-token"

    def test_queue_without_org_repo(self):
        """Verify GitHubQueue can be created without org/repo."""
        queue = GitHubQueue(token="test-token")
        assert queue.org == ""
        assert queue.repo == ""

    def test_repo_api_url(self, queue):
        """Verify _repo_api_url generates correct URL."""
        url = queue._repo_api_url("owner/repo")
        assert url == "https://api.github.com/repos/owner/repo"

    @pytest.mark.asyncio
    async def test_close(self, queue):
        """Verify close() releases the connection pool."""
        await queue.close()
        # Should not raise an error

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_to_queue_success(self, queue, sample_work_item):
        """Verify add_to_queue posts label successfully."""
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels"
        ).mock(
            return_value=httpx.Response(
                200, json={"labels": [{"name": "agent:queued"}]}
            )
        )

        result = await queue.add_to_queue(sample_work_item)
        assert result is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_to_queue_created(self, queue, sample_work_item):
        """Verify add_to_queue returns True on 201 Created."""
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels"
        ).mock(
            return_value=httpx.Response(
                201, json={"labels": [{"name": "agent:queued"}]}
            )
        )

        result = await queue.add_to_queue(sample_work_item)
        assert result is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_to_queue_failure(self, queue, sample_work_item):
        """Verify add_to_queue returns False on failure."""
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels"
        ).mock(return_value=httpx.Response(403, json={"message": "Forbidden"}))

        result = await queue.add_to_queue(sample_work_item)
        assert result is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_queued_tasks_empty(self, queue):
        """Verify fetch_queued_tasks returns empty list when no issues."""
        respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
            return_value=httpx.Response(200, json=[])
        )

        tasks = await queue.fetch_queued_tasks()
        assert tasks == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_queued_tasks_returns_items(self, queue):
        """Verify fetch_queued_tasks returns WorkItems."""
        respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 12345,
                        "number": 42,
                        "html_url": "https://github.com/test-org/test-repo/issues/42",
                        "body": "Test issue",
                        "node_id": "node_123",
                        "labels": [{"name": "agent:queued"}],
                        "title": "Test Issue",
                    }
                ],
            )
        )

        tasks = await queue.fetch_queued_tasks()
        assert len(tasks) == 1
        assert tasks[0].issue_number == 42
        assert tasks[0].task_type == TaskType.IMPLEMENT

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_queued_tasks_detects_plan(self, queue):
        """Verify fetch_queued_tasks detects PLAN task type."""
        respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 12345,
                        "number": 43,
                        "html_url": "https://github.com/test-org/test-repo/issues/43",
                        "body": "Plan issue",
                        "node_id": "node_124",
                        "labels": [{"name": "agent:queued"}, {"name": "agent:plan"}],
                        "title": "Test Plan",
                    }
                ],
            )
        )

        tasks = await queue.fetch_queued_tasks()
        assert tasks[0].task_type == TaskType.PLAN

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_queued_tasks_detects_plan_in_title(self, queue):
        """Verify fetch_queued_tasks detects PLAN from [Plan] in title."""
        respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 12345,
                        "number": 44,
                        "html_url": "https://github.com/test-org/test-repo/issues/44",
                        "body": "Plan issue",
                        "node_id": "node_125",
                        "labels": [{"name": "agent:queued"}],
                        "title": "[Plan] Create new feature",
                    }
                ],
            )
        )

        tasks = await queue.fetch_queued_tasks()
        assert tasks[0].task_type == TaskType.PLAN

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_queued_tasks_detects_bugfix(self, queue):
        """Verify fetch_queued_tasks detects BUGFIX task type."""
        respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 12345,
                        "number": 45,
                        "html_url": "https://github.com/test-org/test-repo/issues/45",
                        "body": "Bug issue",
                        "node_id": "node_126",
                        "labels": [{"name": "agent:queued"}, {"name": "bug"}],
                        "title": "Fix bug",
                    }
                ],
            )
        )

        tasks = await queue.fetch_queued_tasks()
        assert tasks[0].task_type == TaskType.BUGFIX

    @pytest.mark.asyncio
    async def test_fetch_queued_tasks_requires_org_repo(self):
        """Verify fetch_queued_tasks returns empty without org/repo."""
        queue = GitHubQueue(token="test-token")
        tasks = await queue.fetch_queued_tasks()
        assert tasks == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_queued_tasks_rate_limit(self, queue):
        """Verify fetch_queued_tasks raises on rate limit."""
        respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
            return_value=httpx.Response(403, json={"message": "Rate limit exceeded"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await queue.fetch_queued_tasks()

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_queued_tasks_api_error(self, queue):
        """Verify fetch_queued_tasks returns empty on other API errors."""
        respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
            return_value=httpx.Response(500, json={"message": "Internal server error"})
        )

        tasks = await queue.fetch_queued_tasks()
        assert tasks == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_update_status_success(self, queue, sample_work_item):
        """Verify update_status posts label and comment."""
        # Mock delete old label
        respx.delete(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels/agent:in-progress"
        ).mock(return_value=httpx.Response(204))
        # Mock add new label
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels"
        ).mock(
            return_value=httpx.Response(
                200, json={"labels": [{"name": "agent:success"}]}
            )
        )
        # Mock post comment
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/comments"
        ).mock(return_value=httpx.Response(201, json={"id": 1}))

        await queue.update_status(
            sample_work_item, WorkItemStatus.SUCCESS, "Task completed"
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_update_status_scrubs_secrets(self, queue, sample_work_item):
        """Verify update_status scrubs secrets from comments."""
        respx.delete(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels/agent:in-progress"
        ).mock(return_value=httpx.Response(204))
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels"
        ).mock(return_value=httpx.Response(200, json={}))

        comment_route = respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/comments"
        ).mock(return_value=httpx.Response(201, json={"id": 1}))

        # Comment with a fake secret
        await queue.update_status(
            sample_work_item,
            WorkItemStatus.SUCCESS,
            "Token: ghp_FAKEKEYFORTESTING00000000000000000000",
        )

        # Verify the secret was scrubbed
        request = comment_route.calls[0].request
        import json

        body = json.loads(request.content)
        assert "ghp_" not in body["body"]
        assert "***REDACTED***" in body["body"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_claim_task_without_bot_login(self, queue, sample_work_item):
        """Verify claim_task works without bot_login."""
        respx.delete(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels/agent:queued"
        ).mock(return_value=httpx.Response(204))
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels"
        ).mock(return_value=httpx.Response(200, json={}))
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/comments"
        ).mock(return_value=httpx.Response(201, json={"id": 1}))

        result = await queue.claim_task(sample_work_item, "sentinel-123")
        assert result is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_claim_task_with_bot_login(self, queue, sample_work_item):
        """Verify claim_task with bot_login does assign-then-verify."""
        # Assignment
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/assignees"
        ).mock(
            return_value=httpx.Response(
                200, json={"assignees": [{"login": "test-bot"}]}
            )
        )
        # Verify assignment
        respx.get("https://api.github.com/repos/test-org/test-repo/issues/42").mock(
            return_value=httpx.Response(
                200, json={"assignees": [{"login": "test-bot"}]}
            )
        )
        # Label changes
        respx.delete(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels/agent:queued"
        ).mock(return_value=httpx.Response(204))
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/labels"
        ).mock(return_value=httpx.Response(200, json={}))
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/comments"
        ).mock(return_value=httpx.Response(201, json={"id": 1}))

        result = await queue.claim_task(sample_work_item, "sentinel-123", "test-bot")
        assert result is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_claim_task_detects_race_condition(self, queue, sample_work_item):
        """Verify claim_task detects when another sentinel won the race."""
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/assignees"
        ).mock(
            return_value=httpx.Response(
                200, json={"assignees": [{"login": "test-bot"}]}
            )
        )
        # Different assignee - race lost
        respx.get("https://api.github.com/repos/test-org/test-repo/issues/42").mock(
            return_value=httpx.Response(
                200, json={"assignees": [{"login": "other-sentinel"}]}
            )
        )

        result = await queue.claim_task(sample_work_item, "sentinel-123", "test-bot")
        assert result is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_post_heartbeat(self, queue, sample_work_item):
        """Verify post_heartbeat posts a comment."""
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/comments"
        ).mock(return_value=httpx.Response(201, json={"id": 1}))

        await queue.post_heartbeat(sample_work_item, "sentinel-123", 300)

    @respx.mock
    @pytest.mark.asyncio
    async def test_post_heartbeat_handles_error(self, queue, sample_work_item):
        """Verify post_heartbeat handles errors gracefully."""
        respx.post(
            "https://api.github.com/repos/test-org/test-repo/issues/42/comments"
        ).mock(return_value=httpx.Response(500, json={"message": "Error"}))

        # Should not raise
        await queue.post_heartbeat(sample_work_item, "sentinel-123", 300)
