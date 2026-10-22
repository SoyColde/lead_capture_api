from pydantic import BaseModel, Field, EmailStr
from typing import Literal
from enum import Enum
from uuid import UUID
from pydantic import BaseModel

class Valid_Lead(BaseModel):
    name: str = Field(..., description="Nombre del lead")
    email: EmailStr = Field(..., description="Correo electrónico del lead")
    phone: str = Field(..., description="Teléfono del lead")
    request: str = Field(..., description="Solicitud del lead")
    notes: str = Field(description="Notas adicionales del lead")
    temperature: Literal["cold", "hot"] | None = None

class LeadClassification(BaseModel):
    temperature: Literal["cold", "hot"] = Field(..., description="Classification of the lead based on temperature")
    reason: str = Field(..., description="Reason for the classification")

class New_temperature(BaseModel):
    temperature: Literal["cold", "hot"] = Field(..., description="New temperature for the lead")

class Valid_message(BaseModel):
    message: str = Field(..., description="Message to be sent to the assistant")
    conversation_id: UUID | None = None

class LeadStatsArgs(BaseModel):
    status: Literal["cold", "hot"]
    days: int = Field(gt=0)

class LeadByEmailArgs(BaseModel):
    email: EmailStr

class UpdateLeadTemperatureArgs(BaseModel):
    id: int
    new_status: Literal["cold", "hot"]

