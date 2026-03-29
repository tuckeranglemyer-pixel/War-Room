"""
Tests for War Room configuration and tool functions.
Run with: pytest tests/ -v
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig:
    """Test configuration values are properly set."""

    def test_config_imports(self):
        """Config module should import without errors."""
        from src.inference.model_config import LOCAL_MODEL, DAILY_DRIVER_BUYER_MODEL
        assert LOCAL_MODEL is not None
        assert DAILY_DRIVER_BUYER_MODEL is not None

    def test_model_strings_are_valid(self):
        """Model identifiers should follow ollama naming convention."""
        from src.inference.model_config import LOCAL_MODEL, DAILY_DRIVER_BUYER_MODEL
        assert "ollama/" in LOCAL_MODEL or "ollama/" in str(LOCAL_MODEL)
        assert DAILY_DRIVER_BUYER_MODEL is not None


class TestTools:
    """Test ChromaDB tool functions."""

    def test_tools_import(self):
        """Tools module should import without errors."""
        from src.rag import chroma_retrieval
        assert hasattr(chroma_retrieval, '_query_collection') or callable(getattr(chroma_retrieval, 'search_pm_knowledge', None))

    def test_query_collection_exists(self):
        """The _query_collection helper should be defined."""
        from src.rag.chroma_retrieval import _query_collection
        assert callable(_query_collection)


class TestServer:
    """Test FastAPI server endpoints exist."""

    def test_server_imports(self):
        """Server module should import without errors."""
        from src.api import server
        assert hasattr(server, 'app')

    def test_analyze_endpoint_exists(self):
        """POST /analyze endpoint should be registered."""
        from src.api.server import app
        routes = [route.path for route in app.routes]
        assert "/analyze" in routes or any("/analyze" in r for r in routes)

    def test_websocket_endpoint_exists(self):
        """WebSocket /ws/{session_id} endpoint should be registered."""
        from src.api.server import app
        routes = [route.path for route in app.routes]
        assert any("ws" in r for r in routes)
