"""Tests for reusable custom-tool CrewAI adapters."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import custom_tools
import custom_tools.custom_tools as custom_tools_module

from agent.custom_tools import CustomNeo4jTool, get_custom_tools


def test_get_custom_tools_returns_all_wrappers():
    tools = get_custom_tools()

    assert len(tools) == 12
    assert "custom_search_news" in [tool.name for tool in tools]
    assert "custom_get_investments" in [tool.name for tool in tools]


def test_custom_tool_forwards_json_arguments(monkeypatch):
    search_companies = AsyncMock(return_value='[{"name": "Neo4j"}]')
    monkeypatch.setattr(custom_tools, "search_companies", search_companies)
    tool = CustomNeo4jTool(
        name="custom_search_companies",
        description="Search companies",
        target_tool_name="search_companies",
    )

    result = tool._run('{"search": "Neo4j"}')

    assert result == '[{"name": "Neo4j"}]'
    search_companies.assert_awaited_once_with(search="Neo4j")


def test_custom_tools_do_not_initialize_vertex_client_on_import():
    assert custom_tools_module._vertex_client is None


def test_get_investments_uses_local_mcp_when_configured(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_COMMAND", "neo4j-mcp-server")
    mcp_query = AsyncMock(return_value='[{"name": "Contoso"}]')
    monkeypatch.setattr(custom_tools_module, "execute_read_query", mcp_query)

    result = asyncio.run(custom_tools_module.get_investments("Microsoft"))

    assert result == '[{"name": "Contoso"}]'
    mcp_query.assert_awaited_once()


def test_company_query_uses_local_mcp_when_configured(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_COMMAND", "neo4j-mcp-server")
    mcp_query = AsyncMock(return_value='[{"name": "Contoso"}]')
    monkeypatch.setattr(custom_tools_module, "execute_read_query", mcp_query)

    result = asyncio.run(custom_tools.query_company("Contoso"))

    assert result == '{\n  "name": "Contoso"\n}'
    mcp_query.assert_awaited_once()


def test_query_company_uses_demo_database_schema(monkeypatch):
    """The demo graph uses IN_CITY / HAS_CATEGORY / HAS_CEO, not LOCATED_IN etc."""
    monkeypatch.delenv("MCP_SERVER_COMMAND", raising=False)
    calls = []

    class FakeDriver:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute_query(self, query, **params):
            calls.append(query)
            return [], None, None

    monkeypatch.setattr(custom_tools_module, "get_driver", FakeDriver)

    asyncio.run(custom_tools_module.query_company("Neo4j"))

    query = calls[0]
    for missing in ("LOCATED_IN", "IN_INDUSTRY", "WORKS_FOR"):
        assert missing not in query
    for rel in ("IN_CITY", "HAS_CATEGORY", "HAS_CEO", "HAS_BOARD_MEMBER"):
        assert rel in query
