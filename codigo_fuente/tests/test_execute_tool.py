import pytest
from codigo_fuente.tool_registry import execute_tool

def test_unknown_tool():
    with pytest.raises(
        ValueError,
        match="is not registered"
    ):
        execute_tool(
            tool_name="unknown_tool",
            tool_args={},
            db=None
        )

def test_invalid_tool_arguments():
    with pytest.raises(
        ValueError,
        match="Invalid arguments"
    ):
        execute_tool(
            tool_name="get_lead_stats",
            tool_args={
                "days": "siete",
                "status": "hot"
            },
            db=None
        )

