import os
from codigo_fuente.llm_context import save_conversation_turn, MAX_HISTORY_MESSAGES, get_conversation_history, get_or_create_conversation
from dotenv import load_dotenv
from groq import Groq
import json
from codigo_fuente.schemas import LeadClassification
from codigo_fuente.definitions import TOOLS
from codigo_fuente.tool_registry import execute_tool
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

load_dotenv() # It loads environment variables from a .env file,

try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = os.getenv("GROQ_MODEL")
except Exception as e:
    client = None #Autoset client as none since there was a problem with the API key
    model = None

def logg_estimated_cost(conversation_id, total_llm_cost):
    """Registers total cost of a call"""
    logger.info(
        "LLM request total | conversation_id = %s | estimated_cost_usd=%.8f",
        conversation_id,
        total_llm_cost
    )

def log_token_usage(response, operation):
    usage = response.usage

    costo_por_entrada = 0.15 #USD

    costo_entrada_cacheada = 0.075

    charge_per_total_output = 0.60

    cantidad_tokens_por_cobro = 1_000_000

    if usage is None:
        logger.warning(
            "Token usage unavailable for operation %s",
            operation
        )
        return None

    input_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens

    cached_tokens = getattr(
        getattr(usage, "prompt_tokens_details", None),
        "cached_tokens",
        0
    ) or 0

    regular_input_tokens = input_tokens - cached_tokens

    input_cost = (
        regular_input_tokens * costo_por_entrada
        + cached_tokens * costo_entrada_cacheada 
    ) / cantidad_tokens_por_cobro

    output_cost = output_tokens * charge_per_total_output / cantidad_tokens_por_cobro

    estimated_cost = input_cost + output_cost

    logger.info(
        "LLM token usage | operations= %s | Model = %s | input_tokens = %s | output_tokens = %s | total_tokens = %s | estimated cost_usd = %.8f",
        operation,
        response.model,
        input_tokens,
        output_tokens,
        usage.total_tokens,
        estimated_cost,
    )

    return estimated_cost

def classify_lead(lead):
    # It checks if the client is None, which indicates that the LLM client was not initialized properly. 
    # If the client is None, it raises a RuntimeError with a message indicating that the LLM client is not initialized 
    # Suggests checking the GEMINI_API_KEY.
    if client is None or model is None:
        raise RuntimeError("LLM client not initialized or MODEL not set - check your GROQ_API_KEY and MODEL")

    prompt = f"""
    You are a lead classification expert. You will receive information about a lead in JSON format. 

    Your task is to classify the lead as either "cold" (cold) or "hot" (hot) based on the provided information.

    You can consider a lead hot if demonstrates interest in the product or service, and is likely to convert into a customer.
    
    You can consider a lead cold if shows little or no interest in the product or service, and is unlikely to 
    convert into a customer.
    
    Lead Data:
    
    name: {lead.name}
    email: {lead.email}
    phone: {lead.phone}
    request: {lead.request}
    notes: {lead.notes}

    Return only a JSON object with this structure:
    {{
            "temperature": "cold" or "hot",
            "reason": "brief explanation"
    }}

    """

    total_llm_cost = 0.0

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role":"user",
                    "content":prompt
                }
            ],
            response_format={"type":"json_object"}
        )

        call_cost = log_token_usage(response, "classify call")
        
        if call_cost is not None:
            total_llm_cost += call_cost

        result = json.loads(response.choices[0].message.content)

        logger.info("New lead classified successfully")

        logger.info(
            "LLM request total | estimated_cost_usd = %.8f",
            total_llm_cost
        )

        return LeadClassification.model_validate(result)
    
    except Exception as e:
        logger.exception("Unexpected error occurred while classifying lead", extra={"details": str(e)})
        raise ((f"Unexpected error occurred: {e}"))

def send_to_llm(
        message, 
        db, 
        tools=TOOLS,
        conversation_id = None
        ):

    if client is None:
        raise RuntimeError("LLM client not initialized - check your GEMINI_API_KEY")

    system_message = {
    "role": "system",
    "content": (
        "You are a helpful CRM assistant. "
        "Respond in natural, conversational language. "
        "When presenting lead information, prefer concise paragraphs "
        "instead of bullet lists or raw field-by-field output. "
        "Preserve the accuracy of the information returned by tools. "
        "Never invent missing lead information."

        "When a tool returns an error or indicates that"
        "no results were found, explain the situation to "
        "the user in a natural, friendly, and concise manner. "
        "Do not expose exceptions, stack traces, HTTP status codes," 
        "or internal implementation details. Never fabricate results." 
        "If no records are found, clearly explain that no data"
        "matches the requested filters and suggest a useful alternative."
    )
    }

    conversation = get_or_create_conversation(
        db=db,
        conversation_id=conversation_id
    )

    conversation_id = conversation.id

    history = get_conversation_history(
        db=db,
        conversation_id=conversation_id,
        limit=MAX_HISTORY_MESSAGES
    )

    logger.info("History messages loaded: %s", len(history))

    messages = [
        system_message,
        *history[-MAX_HISTORY_MESSAGES:],
        {
            "role":"user",
            "content":message
        }
    ]

    total_llm_cost = 0.0

    try:
        # first call to llm
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        logger.info(f"Message sent to llm successfully: {message}")

        call_cost = log_token_usage(response, "First call")

        if call_cost is not None:
            total_llm_cost += call_cost

        assistant_message = response.choices[0].message

        # Verify if llm requested the function call
        if assistant_message.tool_calls:
            logger.info(f"Function calls received from llm: {assistant_message.tool_calls}")

            tool_call = assistant_message.tool_calls[0]

            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            logger .info(f"Executing tool '{tool_name}' with arguments: {arguments}")

            # Execute the tool and get the result
            try:
                result = execute_tool(tool_name, arguments, db)
            except HTTPException as e:
                result = {
                    "error": True,
                    "status_code": e.status_code,
                    "detail": e.detail,
                }

            if result.get("status") == "approval required":
                logger.info(
                    "Tool '%s' requires human approval; execution blocked.",
                    tool_name
                )

                messages.append(assistant_message)

                messages.append({
                    "role": "system",
                    "content": (
                        "IMPORTANT: The requested action has NOT been "
                        "executed. It requires human approval. "
                        "The pending action has been registered, but "
                        "the lead has not been modified. "
                        "Respond naturally in the user's language. "
                        "Clearly explain that approval is required. "
                        "Never claim that the change was completed."
                    )
                })

                messages.append(
                                {
                                    "role":"tool",
                                    "tool_call_id":tool_call.id,
                                    "content":json.dumps(result, default=str)
                                }
                            )

                final_response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
                                    )

                call_cost = log_token_usage(final_response, "approval_required")
                
                if call_cost is not None:
                    total_llm_cost += call_cost

                logger.info(
                    "Natural-language response generated for pending approval."
                )

                assistant_text = (
                    final_response.choices[0].message.content or ""
                )

                save_conversation_turn(
                    db=db,
                    conversation_id=conversation_id,
                    assistant_message = assistant_text,
                    user_message=message,
                )

                logg_estimated_cost(conversation_id, total_llm_cost)

                return final_response, str(conversation.id)

            logger.info("Tool '%s' executed successfully.", tool_name)

            # Created the new content with the result
            messages.append(assistant_message)

            messages.append(
                {
                    "role":"tool",
                    "tool_call_id":tool_call.id,
                    "content":json.dumps(result, default=str)
                }
            )

            # Send the result back to llm
            final_response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            logger.info("Final response generated succesfully") 
            
            call_cost = log_token_usage(final_response, "tool_executed")
            
            if call_cost is not None:
                total_llm_cost += call_cost

            assistant_text = (
                                final_response.choices[0].message.content or ""
                            )
            
            save_conversation_turn(
                                db=db,
                                conversation_id=conversation_id,
                                user_message=message,
                                assistant_message=assistant_text
                            )

            logg_estimated_cost(conversation_id, total_llm_cost)

            return final_response, str(conversation.id)

        logger.info("No function calls received from llm, returning the initial response")

        assistant_text = response.choices[0].message.content or ""

        save_conversation_turn(
            db=db,
            conversation_id=conversation_id,
            user_message=message,
            assistant_message=assistant_text
        )

        logg_estimated_cost(conversation_id, total_llm_cost)

        return response, str(conversation.id)

    except Exception as e:
        logger.exception("Unexpected error occurred while sending message to llm", extra={"details": str(e)})
        raise RuntimeError(f"Unexpected error occurred: {e}")


