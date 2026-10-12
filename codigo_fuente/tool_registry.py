# Tool registration for calling
import codigo_fuente.llm_tools_functions as llm_tools
from codigo_fuente.schemas import LeadStatsArgs, LeadByEmailArgs, UpdateLeadTemperatureArgs
from pydantic import ValidationError

TOOL_REGISTRY = {
    "get_lead_stats": {
        "function":llm_tools.get_lead_stats,
        "schema": LeadStatsArgs,
        "requires_confirmation": False
    },
    "get_lead_by_email": {
        "function": llm_tools.get_lead_by_email,
        "schema": LeadByEmailArgs,
        "requires_confirmation": False
    },
    "update_lead_temperature": {
        "function": llm_tools.update_lead_temperature,
        "schema": UpdateLeadTemperatureArgs,
        "requires_confirmation": True
    }
}

def execute_tool(tool_name, tool_args, db):
    """
    Executes a tool from the TOOL_REGISTRY with the provided arguments.
    """
    tool = TOOL_REGISTRY.get(tool_name)

    if not tool:
        raise ValueError(f"Tool '{tool_name}' is not registered.")

    try:
        validated_args = tool["schema"].model_validate(tool_args)
    except ValidationError as e:
        raise ValueError(f"Invalid arguments for tool '{tool_name}': {e}")

    return tool["function"](**validated_args.model_dump(), db=db)