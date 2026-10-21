# Tool registration for calling
import codigo_fuente.llm_tools_functions as llm_tools
from codigo_fuente.schemas import LeadStatsArgs, LeadByEmailArgs, UpdateLeadTemperatureArgs
from pydantic import ValidationError
from codigo_fuente.models import PendingAction

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

def execute_tool(tool_name, tool_args, db, requested_by="ADMIN"):
    """
    Executes a tool from the TOOL_REGISTRY with the provided arguments.
    If requires confirmation, saves the request info
    """
    tool = TOOL_REGISTRY.get(tool_name)

    if not tool:
        raise ValueError(f"Tool '{tool_name}' is not registered.")
    
    # Validates args before any execution
    try:
        validated_args = tool["schema"].model_validate(tool_args)        
    except ValidationError as e:
        raise ValueError(f"Invalid arguments for tool '{tool_name}': {e}")


    if tool["requires_confirmation"]:

        pending_action = PendingAction(
            tool_name=tool_name,
            arguments = validated_args.model_dump(),
            status="pending",
            requested_by=requested_by,
        )

        # Save as a new row in table
        try:
            db.add(pending_action)
            db.commit()
            db.refresh(pending_action)

        except Exception:
            db.rollback()
            raise

        
        return {
                "status":"approval required",
                "approval_id": pending_action.id,
                "tool":pending_action.tool_name,
                "arguments":pending_action.arguments,
                "message":(
                    "The action requires human approval. "
                    "The tool has not been executed."
                           ),
            }

    # Since not approval required, executed as normal

    return tool["function"](**validated_args.model_dump(), db=db, )