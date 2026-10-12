from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, HTTPException, Depends, Query
from codigo_fuente.database import engine, Base
from codigo_fuente.dependencies import get_db, verify_api_key
from codigo_fuente.models import Lead
from codigo_fuente.schemas import Valid_Lead, Valid_message
from codigo_fuente.llm_service import classify_lead, send_to_llm
import math
import logging
import codigo_fuente.logging_config
from google.genai.errors import ServerError

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

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

    except ServerError as e:
    #It catches the ServerError exception raised by the clasify_lead function when there is a server error while using the LLM. 
        logger.error("Server error from LLM", extra={"details": str(e)})
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
    response = send_to_llm(question.message, db)
    if response.choices:
        content=response.choices[0].message.content
    if content is None:
        raise HTTPException(status_code=502, detail="The LLM returned an empty response")
    logger.info(f"Assistant question processed successfully: {question.message}")
    return {"response": response.choices[0].message.content, "message": "Assistant question processed successfully"}
