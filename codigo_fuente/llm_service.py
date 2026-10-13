import os
from dotenv import load_dotenv
from groq import Groq
import json
from codigo_fuente.schemas import LeadClassification
from codigo_fuente.definitions import TOOLS
from codigo_fuente.tool_registry import execute_tool
import logging

logger = logging.getLogger(__name__)

load_dotenv() # It loads environment variables from a .env file,

try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = os.getenv("GROQ_MODEL")
except Exception as e:
    client = None #Autoset client as none since there was a problem with the API key
    model = None

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

    Return only a JSON object with this structure:{
            "temperature": "cold" or "hot",
            "reason": "brief explanation"
    }

    """

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

        result = json.loads(response.choices[0].message.content)

        return LeadClassification.model_validate(result)
    
    except Exception as e:
        logger.exception("Unexpected error occurred while classifying lead", extra={"details": str(e)})
        raise ((f"Unexpected error occurred: {e}"))

def send_to_llm(message, db, tools=TOOLS):

    if client is None:
        raise RuntimeError("LLM client not initialized - check your GEMINI_API_KEY")

    messages = [
        {
    "role": "system",
    "content": (
        "You are a helpful CRM assistant. "
        "Respond in natural, conversational language. "
        "When presenting lead information, prefer concise paragraphs "
        "instead of bullet lists or raw field-by-field output. "
        "Preserve the accuracy of the information returned by tools. "
        "Never invent missing lead information."
    )
},
        {
            "role":"user",
            "content": message
        }
    ]

    try:
        # first call to llm
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        logger.info(f"Message sent to llm successfully: {message}")

        assistant_message = response.choices[0].message

        # Verify if llm requested the function call
        if assistant_message.tool_calls:
            logger.info(f"Function calls received from llm: {assistant_message.tool_calls}")

            tool_call = assistant_message.tool_calls[0]

            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            logger .info(f"Executing tool '{tool_name}' with arguments: {arguments}")

            # Execute the tool and get the result
            result = execute_tool(tool_name, arguments, db)

            if result.get("status") == "approval required":
                logger.info(
                    "Tool '%s' requires human approval; execution blocked.",
                    tool_name
                )

                return {
                    "status":"approval required",
                    "tool": tool_name,
                    "arguments":result["arguments"],
                    "message": "Human approval is required before execution",
                }

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

            return final_response

        logger.info("No function calls received from Gemini, returning the initial response")

        return response
    
    except Exception as e:
        logger.exception("Unexpected error occurred while sending message to llm", extra={"details": str(e)})
        raise RuntimeError(f"Unexpected error occurred: {e}")


