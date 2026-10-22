# Tool registration for calling
import codigo_fuente.llm_tools_functions as llm_tools
from codigo_fuente.schemas import LeadStatsArgs, LeadByEmailArgs, UpdateLeadTemperatureArgs
from pydantic import ValidationError
from codigo_fuente.models import PendingAction
import hashlib
import json
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

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

def normalize_arguments(arguments: dict) -> str:
    return json.dumps(
        arguments,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

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

        arguments = validated_args.model_dump(mode="json")

        normalized_args = normalize_arguments(arguments)

        #Generate a stable lock key
        lock_source = f"{tool_name}:{normalized_args}"
        lock_id = int.from_bytes(
            hashlib.sha256(lock_source.encode("utf-8")).digest()[:8],
            byteorder="big",
            signed=True,
        )

        try:

            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": lock_id},
            )

            pending_actions = (
                db.query(PendingAction)
                .filter(
                    PendingAction.tool_name == tool_name,
                    PendingAction.status == "pending",
                )
                .all()
            )

            for existing in pending_actions:
                existing_args = normalize_arguments(existing.arguments)

                if existing_args == normalized_args:
                    db.commit()

                    return {
                        "status":"already pending",
                        "approval_id":existing.id,
                        "tool":existing.tool_name,
                        "arguments":existing.arguments,
                        "message":(
                            "An identical request is already awaiting "
                            "human approval. No duplicate was created"
                        ),
                    }
                
            # No duplicates were found: Create the request.
            pending_action = PendingAction(
                tool_name=tool_name,
                arguments=arguments,
                status="pending",
                requested_by=requested_by,
            )

            # Save as a new row in table
            db.add(pending_action)
            db.commit()
            db.refresh(pending_action)

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

        except Exception as e:
            logger.error(f"Error encontrado durante la ejecucion, {e}")
            db.rollback()
            raise    
    # Since not approval required, executed as normal

    return tool["function"](**validated_args.model_dump(), db=db, )