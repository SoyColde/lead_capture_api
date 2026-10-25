from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from codigo_fuente.main import app, verify_api_key, get_db
from codigo_fuente import llm_service
from codigo_fuente.llm_service import send_to_llm

client = TestClient(app, raise_server_exceptions=False)

def create_tool_response():
    """Simulates the first LLM call requesting a tool"""

    tool_call = SimpleNamespace(
        id = "call_test_123",
        function=SimpleNamespace(
            name="unknown_tool",
            arguments="{}",
        ),
    )

    message = SimpleNamespace(
        tool_calls=[tool_call],
        content=None,
    )

    return SimpleNamespace(
        choices = [SimpleNamespace(message=message)],
        usage = None,
        model ="test-model",
    )

def create_final_response():
    """Simulates final response from LLM after error."""

    message = SimpleNamespace(
        tool_calls = None,
        content="Unable to execute requested tool"
    )

    return SimpleNamespace(
        choices = [SimpleNamespace(message=message)],
        usage=None,
        model="test-model", 
    )

def test_assistant_ask_handles_value_error_without_500():
    # First response: LLM calls a none existent tool
    first_response = create_tool_response()

    # Second response: LLM answers after receiving an error
    final_response = create_final_response()

    # Save original dependencies to restore it
    previous_override = app.dependency_overrides.copy()

    # Avoid Auth and DB to interrupt    

    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()

    try:
        with (
            patch.object(
                llm_service.client.chat.completions,
                "create",
                side_effect=[first_response, final_response],
            ) as mock_llm,
            patch.object(
                llm_service,
                "execute_tool",
                side_effect=ValueError("Tool does not exist"),
            ) as mock_execute_tool,
            patch.object(
                llm_service,
                "get_or_create_conversation",
                return_value = SimpleNamespace(
                    id="test-conversation-id"
                ),

            ),
            patch.object(
                llm_service,
                "get_conversation_history",
                return_value = [],
            ),
            patch.object(
                llm_service,
                "save_conversation_turn",
            ),
            patch.object(
                llm_service,
                "logg_estimated_cost",
            ),
            patch.object(
                llm_service,
                "log_token_usage",
                return_value=None
            ),
        ):
            response = client.post(
                "/assistant/ask",
                json={"message": "Consult the leads"},
            )

        # Verify execute a tool was attempted
        mock_execute_tool.assert_called_once()

        # Verify the LLM received two calls
        # Initial request and final one

        assert mock_llm.call_count == 2

        # Verify endpoint did not return http 500.
        assert response.status_code != 500, (
            f"HTTP {response.status_code}: {response.text}"
        )

        # Veridy that the result was sent to LLM in the second call
        second_call_messages = (mock_llm.call_args_list[1].kwargs["messages"])

        tool_messages = [
            message
            for message in second_call_messages
            if isinstance(message, dict)
            and message.get("role") == "tool"
        ]

        assert tool_messages

        assert "Tool does not exist" in tool_messages[-1]["content"]

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_override)