"""Pytest configuration and fixtures for OS-APOW tests."""

import pytest
import os
import sys

# Ensure the src directory is on the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token-12345")
    monkeypatch.setenv("GITHUB_ORG", "test-org")
    monkeypatch.setenv("GITHUB_REPO", "test-repo")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret-12345")


@pytest.fixture
def sample_issue_payload():
    """Sample GitHub issue webhook payload."""
    return {
        "action": "opened",
        "issue": {
            "id": 12345,
            "number": 42,
            "html_url": "https://github.com/test-org/test-repo/issues/42",
            "body": "Test issue body",
            "node_id": "node_123",
            "title": "[Application Plan] Test Feature",
            "labels": [],
        },
        "repository": {
            "full_name": "test-org/test-repo",
            "id": 98765,
        },
    }
