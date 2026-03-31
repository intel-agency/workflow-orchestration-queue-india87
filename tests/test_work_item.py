"""Tests for the work_item module."""

import pytest
from src.models.work_item import TaskType, WorkItemStatus, WorkItem, scrub_secrets


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_values(self):
        """Verify TaskType enum has expected values."""
        assert TaskType.PLAN.value == "PLAN"
        assert TaskType.IMPLEMENT.value == "IMPLEMENT"
        assert TaskType.BUGFIX.value == "BUGFIX"

    def test_task_type_is_string(self):
        """Verify TaskType inherits from str."""
        assert isinstance(TaskType.PLAN, str)
        assert isinstance(TaskType.IMPLEMENT, str)
        assert isinstance(TaskType.BUGFIX, str)


class TestWorkItemStatus:
    """Tests for WorkItemStatus enum."""

    def test_status_values(self):
        """Verify WorkItemStatus enum has expected label values."""
        assert WorkItemStatus.QUEUED.value == "agent:queued"
        assert WorkItemStatus.IN_PROGRESS.value == "agent:in-progress"
        assert WorkItemStatus.RECONCILING.value == "agent:reconciling"
        assert WorkItemStatus.SUCCESS.value == "agent:success"
        assert WorkItemStatus.ERROR.value == "agent:error"
        assert WorkItemStatus.INFRA_FAILURE.value == "agent:infra-failure"
        assert WorkItemStatus.STALLED_BUDGET.value == "agent:stalled-budget"

    def test_status_is_string(self):
        """Verify WorkItemStatus inherits from str."""
        assert isinstance(WorkItemStatus.QUEUED, str)
        assert isinstance(WorkItemStatus.SUCCESS, str)


class TestWorkItem:
    """Tests for WorkItem model."""

    def test_work_item_creation(self):
        """Verify WorkItem can be created with all fields."""
        item = WorkItem(
            id="12345",
            issue_number=42,
            source_url="https://github.com/org/repo/issues/42",
            context_body="Test issue body",
            target_repo_slug="org/repo",
            task_type=TaskType.IMPLEMENT,
            status=WorkItemStatus.QUEUED,
            node_id="node_123",
        )
        assert item.id == "12345"
        assert item.issue_number == 42
        assert item.source_url == "https://github.com/org/repo/issues/42"
        assert item.context_body == "Test issue body"
        assert item.target_repo_slug == "org/repo"
        assert item.task_type == TaskType.IMPLEMENT
        assert item.status == WorkItemStatus.QUEUED
        assert item.node_id == "node_123"

    def test_work_item_with_plan_type(self):
        """Verify WorkItem with PLAN task type."""
        item = WorkItem(
            id="1",
            issue_number=1,
            source_url="https://github.com/org/repo/issues/1",
            context_body="Plan content",
            target_repo_slug="org/repo",
            task_type=TaskType.PLAN,
            status=WorkItemStatus.QUEUED,
            node_id="node_1",
        )
        assert item.task_type == TaskType.PLAN

    def test_work_item_with_empty_context(self):
        """Verify WorkItem with empty context body."""
        item = WorkItem(
            id="2",
            issue_number=2,
            source_url="https://github.com/org/repo/issues/2",
            context_body="",
            target_repo_slug="org/repo",
            task_type=TaskType.BUGFIX,
            status=WorkItemStatus.QUEUED,
            node_id="node_2",
        )
        assert item.context_body == ""


class TestScrubSecrets:
    """Tests for the scrub_secrets function."""

    def test_scrub_github_pat_classic(self):
        """Verify GitHub PAT (classic) is redacted."""
        text = "Token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        result = scrub_secrets(text)
        assert "ghp_" not in result
        assert "***REDACTED***" in result

    def test_scrub_github_app_token(self):
        """Verify GitHub App installation token is redacted."""
        text = "Token: ghs_1234567890abcdefghijklmnopqrstuvwxyz"
        result = scrub_secrets(text)
        assert "ghs_" not in result
        assert "***REDACTED***" in result

    def test_scrub_github_oauth_token(self):
        """Verify GitHub OAuth token is redacted."""
        text = "Token: gho_1234567890abcdefghijklmnopqrstuvwxyz"
        result = scrub_secrets(text)
        assert "gho_" not in result
        assert "***REDACTED***" in result

    def test_scrub_github_fine_grained_pat(self):
        """Verify GitHub fine-grained PAT is redacted."""
        text = "Token: github_pat_22ABCDEFGHabcdefghijklmnopqrstuvwxyz"
        result = scrub_secrets(text)
        assert "github_pat_" not in result
        assert "***REDACTED***" in result

    def test_scrub_bearer_token(self):
        """Verify Bearer token is redacted."""
        text = "Authorization: Bearer abc123xyz789=="
        result = scrub_secrets(text)
        assert "Bearer abc123xyz789" not in result
        assert "***REDACTED***" in result

    def test_scrub_openai_key(self):
        """Verify OpenAI-style API key is redacted."""
        text = "API Key: sk-1234567890abcdefghijklmnop"
        result = scrub_secrets(text)
        assert "sk-1234567890" not in result
        assert "***REDACTED***" in result

    def test_scrub_zhipuai_key(self):
        """Verify ZhipuAI key is redacted."""
        text = "Key: abcdefghijklmnopqrstuvwxyz123456.zhipuABC"
        result = scrub_secrets(text)
        assert ".zhipu" not in result
        assert "***REDACTED***" in result

    def test_scrub_multiple_secrets(self):
        """Verify multiple secrets are redacted."""
        text = "ghp_1234567890abcdefghijklmnopqrstuvwxyz and sk-abcdefghijklmnopqrstuv"
        result = scrub_secrets(text)
        assert "ghp_" not in result
        assert "sk-" not in result
        assert result.count("***REDACTED***") == 2

    def test_scrub_no_secrets(self):
        """Verify text without secrets is unchanged."""
        text = "This is a normal log message without any secrets."
        result = scrub_secrets(text)
        assert result == text

    def test_scrub_custom_replacement(self):
        """Verify custom replacement string works."""
        text = "Token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        result = scrub_secrets(text, replacement="[HIDDEN]")
        assert "[HIDDEN]" in result
        assert "ghp_" not in result

    def test_scrub_empty_string(self):
        """Verify empty string returns empty."""
        result = scrub_secrets("")
        assert result == ""

    def test_scrub_preserves_surrounding_text(self):
        """Verify surrounding text is preserved."""
        text = (
            "Starting job with token ghp_1234567890abcdefghijklmnopqrstuvwxyz for repo"
        )
        result = scrub_secrets(text)
        assert result.startswith("Starting job with token ***REDACTED*** for repo")
