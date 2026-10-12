from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from sqlalchemy import func
from codigo_fuente.dependencies import get_db
from sqlalchemy.orm import Session
from codigo_fuente.models import Lead
from codigo_fuente.schemas import New_temperature
import logging


logger = logging.getLogger(__name__)

def get_lead_stats(db: Session, status: str = None, days: int = None):
    """This function retrieves lead statistics based on the provided status."""
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.temperature == status)
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Lead.created_at >= cutoff)
    if query.count() == 0:
        logger.warning(f"No leads found with status: {status} and within the last {days} days")
        raise HTTPException(status_code=404, detail={
            "error": "No leads found", "details": f"No leads found with status: {status} and within the last {days} days"})

    total_leads = query.count()
    logger.info(f"Retrieved lead stats - Total leads: {total_leads}, Status: {status}, Days: {days}")
    return {"total_leads": total_leads, "status": status, "days": days}

def get_lead_by_email(email: str, db: Session):
    """This function retrieves a lead based on the provided email."""
    lead = db.query(Lead).filter(func.lower(Lead.email) == func.lower(email)).first()
    if lead is None:
        logger.warning(f"Lead not found with email: {email}")
        return {
            "found": False,
            "message": "Lead does not exist with that email."
        }
    logger.info("Lead retrieved successfully")
    return {
        "found": True,
        "lead": {
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "temperature": lead.temperature,
            "notes": lead.notes
        }
    }

def update_lead_temperature(id: int, new_status: New_temperature, db: Session):
    """This function updates the temperature of a lead based on the provided ID."""
    lead = db.query(Lead).filter(Lead.id == id).first()

    try:
        if lead:
            lead.temperature = new_status
            db.commit()
            logger.info(f"Lead temperature updated successfully for ID: {lead.id} to {lead.temperature}")
            return {"id": lead.id, "temperature": lead.temperature}
        else:
            raise HTTPException(status_code=404, detail={
                "error": "Lead not found", "details": f"No lead found with ID: {id}"})
    except Exception as e:
        logger.exception("Unexpected error occurred while updating lead temperature", extra={"details": str(e)})
        db.rollback()
        raise e