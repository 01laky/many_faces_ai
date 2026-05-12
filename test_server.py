#!/usr/bin/env python3
"""
test_server.py - Unit tests for AI Demo gRPC server

Tests the HealthService gRPC methods using pytest and grpcio-testing.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.grpc

# Repo root (ai_demo) on path: `proto` package + `server` module
_APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

try:
    import grpc  # noqa: F401 - availability check, used in TestServerIntegration
    import grpc_testing  # noqa: F401 - availability check

    import server

    health_pb2 = server.health_pb2
    health_pb2_grpc = server.health_pb2_grpc
    HealthServiceServicer = server.HealthServiceServicer
except ImportError as e:
    pytest.skip(f"Skipping gRPC tests: {e}", allow_module_level=True)


class TestHealthServiceServicer:
    """Test suite for HealthServiceServicer"""

    @pytest.fixture
    def servicer(self):
        """Create HealthServiceServicer instance"""
        return HealthServiceServicer()

    @pytest.fixture
    def mock_context(self):
        """Create mock gRPC context"""
        context = MagicMock()
        context.code = lambda: None
        context.details = lambda: None
        return context

    def test_health_check_returns_success(self, servicer, mock_context):
        """Test that HealthCheck returns success response"""
        # Arrange
        request = health_pb2.HealthCheckRequest()

        # Act
        response = servicer.HealthCheck(request, mock_context)

        # Assert
        assert response is not None
        assert response.status == "success"
        assert response.message == "AI Demo service is running and ready"
        assert "running" in response.message.lower()
        assert "ready" in response.message.lower()

    def test_health_check_request_type(self, servicer, mock_context):
        """Test that HealthCheck accepts HealthCheckRequest"""
        # Arrange
        request = health_pb2.HealthCheckRequest()

        # Act
        response = servicer.HealthCheck(request, mock_context)

        # Assert
        assert isinstance(response, health_pb2.HealthCheckResponse)

    def test_health_check_multiple_calls(self, servicer, mock_context):
        """Test that HealthCheck can be called multiple times"""
        # Arrange
        request = health_pb2.HealthCheckRequest()

        # Act - call multiple times
        response1 = servicer.HealthCheck(request, mock_context)
        response2 = servicer.HealthCheck(request, mock_context)
        response3 = servicer.HealthCheck(request, mock_context)

        # Assert
        assert response1.status == "success"
        assert response2.status == "success"
        assert response3.status == "success"
        assert response1.message == response2.message == response3.message

    def test_review_content_returns_structured_approval_recommendation(self, servicer, mock_context):
        """Test baseline content moderation response shape for safe content"""
        request = health_pb2.ContentReviewRequest(
            content_type="Blog",
            content_id=42,
            moderation_version=1,
            face_id=1,
            title="Community update",
            body="A normal update for the community.",
            creator_id="user-1",
        )

        response = servicer.ReviewContent(request, mock_context)

        assert response.decision == "approve"
        assert response.risk_level == "low"
        assert 0 <= response.confidence <= 1
        assert response.model_version == "moderation-heuristic-v1"
        assert response.trace_id.startswith("ai-review-")
        assert response.error == ""

    def test_review_content_flags_unsafe_content(self, servicer, mock_context):
        """Test baseline moderation detects unsafe terms and recommends rejection"""
        request = health_pb2.ContentReviewRequest(
            content_type="Reel",
            content_id=43,
            moderation_version=1,
            face_id=1,
            title="Adult spam",
            body="This looks like adult scam content.",
            media_url="javascript:alert(1)",
            creator_id="user-1",
        )

        response = servicer.ReviewContent(request, mock_context)

        assert response.decision == "reject"
        assert response.risk_level == "high"
        assert "adult" in response.flags
        assert "spam" in response.flags
        assert "unsafe_link" in response.flags


class TestServerIntegration:
    """Integration tests for gRPC server"""

    def test_health_service_registration(self):
        """Test that HealthService can be registered on server"""
        # Arrange
        from concurrent import futures

        import grpc

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

        # Act
        health_pb2_grpc.add_HealthServiceServicer_to_server(HealthServiceServicer(), server)

        # Assert - no exception should be raised
        assert server is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
