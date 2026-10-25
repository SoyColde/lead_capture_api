from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, HTTPException, Depends, Query
from codigo_fuente.database import engine, Base
from codigo_fuente.dependencies import get_db, verify_api_key
from codigo_fuente.models import Lead, PendingAction
from codigo_fuente.schemas import Valid_Lead, Valid_message
from codigo_fuente.llm_service import classify_lead, send_to_llm
from codigo_fuente.tool_registry import TOOL_REGISTRY
from datetime import datetime, timezone
import math
import logging
import codigo_fuente.logging_config
from typing import Literal

logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/leads", status_code=201)
def create_lead(lead: Valid_Lead, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    # endpoint to receive lead data and create a new lead) 

    if lead.temperature:
        logger.warning("Temperature field was provided in the request, which is not allowed")
        raise HTTPException(status_code=422, detail={"error": "Temperature field should not be provided"})
    new_lead = Lead(
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            request=lead.request,
            notes=lead.notes)
    
    # Handle duplicate email or phone number
    try:
        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"Lead with this email or phone number already exists: {e}")
        raise HTTPException(status_code=409, detail={"error": "Lead with this email or phone number already exists", 
                                                     "details": "Email or phone number already in use"})

    

    try:
        result = classify_lead(new_lead)

        new_lead.temperature = result.temperature

        db.commit()

    except RuntimeError as e:
    #It catches the RuntimeError exception raised by the clasify_lead function when the LLM client is unavailable. 
        logger.error("LLM client unavailable", extra={"details": str(e)})
        new_lead.temperature = "pending"
        db.commit()
        
    except Exception as e:
    #It catches any other unexpected exceptions raised by the clasify_lead function.
        logger.exception("Unexpected classification error", extra={"details": str(e)})
        new_lead.temperature = "pending"
        db.commit()

    db.refresh(new_lead)

    logger.info(f"Lead created successfully with ID: {new_lead.id} and temperature: {new_lead.temperature}")

    return {"message": "Lead created successfully", 
            "id": new_lead.id,
            "temperature": new_lead.temperature
            }

@app.get("/leads", status_code=200)
def get_leads(limit: int = Query(10, ge=1, le=100, description="Number of leads to retrieve per page (1-100)"),
              pages: int = Query(1, ge=1, description="Page number to retrieve (1-based)"),
              db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """This retrieves a list of leads from the database, with optional pagination parameters (limit and pages)."""

    offset = (pages - 1) * limit

    total_leads = db.query(Lead).count()

    if total_leads:
        total_pages = math.ceil(total_leads / limit)
    else:
        total_pages = 0
        logger.warning("No leads found in the database")
        raise HTTPException(status_code=404, detail={"error": "No leads found", "details": "The database is empty"})

    leads = (db.query(Lead)
             .offset(offset)
             .limit(limit)
             .all()
            )

    logger.info(f"Retrieved {len(leads)} leads (Page {pages} of {total_pages})")
    
    return {"pages": pages,
            "limit": limit,
            "total_leads": total_leads,
            "total_pages": total_pages,
            "leads": leads}

@app.get("/leads/{id}", status_code=200)
def get_lead(id: int, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """This retrieves a specific lead from the database based on the provided ID."""
    
    lead = db.query(Lead).filter(Lead.id == id).first()
    
    if not lead:
        logger.warning(f"Lead not found with ID: {id}")
        raise HTTPException(status_code=404, detail={"error": "Lead not found", "details": f"No lead found with ID: {id}"})
    
    logger.info(f"Lead retrieved successfully with ID: {lead.id}")
    return lead

@app.patch("/leads/{id}", status_code=200)
def update_lead(id: int, lead: Valid_Lead, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """This updates a specific lead in the database based on the provided ID and new lead data."""
    
    existing_lead = db.query(Lead).filter(Lead.id == id).first()
    
    if not existing_lead:
        logger.warning(f"Lead not found with ID: {id}")
        raise HTTPException(status_code=404, detail={"error": "Lead not found", "details": f"No lead found with ID: {id}"})
    
    try:
        existing_lead.name = lead.name
        existing_lead.email = lead.email
        existing_lead.phone = lead.phone
        existing_lead.request = lead.request
        existing_lead.notes = lead.notes
        if lead.temperature:
            existing_lead.temperature = lead.temperature
            
        
        db.commit()
        db.refresh(existing_lead)
        
    except IntegrityError:
        db.rollback()
        logger.warning(f"Lead with this email or phone number already exists: {lead.email}, {lead.phone}")
        raise HTTPException(status_code=409, detail={"error": "Lead with this email or phone number already exists", 
                                                     "details": "Email or phone number already in use"})
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error occurred", extra={"details": str(e)})
        raise HTTPException(status_code=422, detail={"error": "Unexpected error occurred", "details": str(e)})

    logger.info(f"Lead updated successfully with ID: {existing_lead.id}")
    
    return {"message": "Lead updated successfully", 
            "id": existing_lead.id,
            "temperature": existing_lead.temperature
            }

@app.post("/assistant/ask", status_code=200)
def ask_assistant(question: Valid_message, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db)):
    """This endpoint allows users to ask questions to the assistant."""
    content = None
    response, conversation_id = send_to_llm(message=question.message, 
                                            db=db, 
                                            conversation_id=question.conversation_id)

    # Case 1: A tool requires human approval
    if isinstance(response, dict) and response.get("status") == "approval required":

        logger.info(
            "Human approval required for tool '%s'.",
            response["tool"],
        )

        return {
            "Conversation_id":conversation_id,
            "response":response,
            }

    
    # Case 2: The LLM returned a normal response.
    if not response.choices:
        raise HTTPException(
            status_code=502,
            detail="The LLM returned an empty response",
        )

    content = response.choices[0].message.content

    if content is None:
        raise HTTPException(
            status_code=502,
            detail="The LLM returned an empty response",
        )

    logger.info("Assistant question processed successfully.")

    return {
        "status": "completed",
        "conversation_id": conversation_id,
        "response": content,
        "message": "Assistant question processed successfully",
    }

@app.get("/actions/{action_status}", status_code=200)
def get_pending_actions(
    action_status: Literal["executed", "rejected", "pending"],
    limit: int = Query(10, ge=1, le=100, description="Number of requests to retrieve per page (1-100)"),
              pages: int = Query(1, ge=1, description="Page number to retrieve (1-based)"),
              db: Session = Depends(get_db), api_key: str = Depends(verify_api_key),
            ):
    """
    Retrieves all the pending actions registered
    """

    offset = (pages - 1) * limit

    query = db.query(PendingAction).filter(PendingAction.status == action_status)

    total_requests = query.count()

    if total_requests:
        total_pages = math.ceil(total_requests / limit) 
    else:
        total_pages = 0
        logger.warning("No actions found in the database")
        raise HTTPException(status_code=404, detail={"requests": "0", "details": "The database is empty"})

    actions = (query
               .order_by(PendingAction.id.asc())
               .offset(offset)
               .limit(limit)
               .all()
            )

    logger.info(f"Retrieved {len(actions)} pending actions (Page {pages} of {total_pages})")
    
    return {"pages": pages,
            "limit": limit,
            "total_requests": total_requests,
            "total_pages": total_pages,
            "requests": actions}

@app.post("/pending_actions/{action_id}/{new_status}")
def approve_pending_action(
    action_id: int,
    new_status: Literal["approve", "reject"],
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):

    """
    Process pending actions exactly once
    """

    try:
    # Lock the action row while processing it
        action = (
                    db.query(PendingAction)
                    .filter(PendingAction.id == action_id)
                    .with_for_update()
                    .first()
                )
    
        if action is None:
            raise HTTPException(
                        status_code=404,
                        detail="Pending action not found",
                    )
    
        # Only process pending actions
        if action.status != "pending":
            raise HTTPException(
                        status_code = 409,
                        detail=(
                            "Action cannot be processed "
                            f"Current status is {action.status}."
                        ),
                    )

        if new_status == "approve":
            """
            Approve and execute pending actions exactly once
            """

            # Resolves the tool from the registry
            tool = TOOL_REGISTRY.get(action.tool_name)

            if tool is None or not tool["requires_confirmation"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or non-approvable tool",
                )

            # Revalidated the arguments stored in the database

            validated_args = tool["schema"].model_validate(action.arguments)

            # Record the approval within the transaction

            action.status = "approved"
            action.approved_by = "api_key_authenticated"

            db.flush()

            # Execute tool
            result = tool["function"](
                **validated_args.model_dump(),
                db=db,
            )

            action.status = "executed"
            action.executed_at = datetime.now(timezone.utc)


        elif new_status == "reject":
            action.status = "rejected"
            result = "Action rejected. The tool was not executed."


        now = datetime.now(timezone.utc)
        action.decided_at = now
        logger.info(f"Action processed succesfully: {action.status} with the id: {action.id} and {result}")

        db.commit()

        return {
                "approval_id": action.id,
                "status": action.status,
                "result": result,
            } 

    except HTTPException as e:
            logger.error(f"Error while processing the request, details {e}")
            db.rollback()
            raise
    except Exception:
            db.rollback()
            logger.exception(
                f"Failed to {new_status} pending action %s",
                action_id,
            )
            raise HTTPException(
                status_code = 500,
                detail= f"Failed to {new_status} and execute the action",
            )
