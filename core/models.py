from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date

class Transaction(BaseModel):
    """
    Pydantic model representing a financial transaction extracted from natural language input.
    This model defines the expected structure of the transaction data, including
    validation rules (e.g., positive amount) and optional fields for account information.
    
    """
    date: date
    # Restringimos las opciones para que Gemini no invente tipos de movimiento
    transaction_type: Literal["Ingreso", "Gasto", "Traspaso"]
    amount: float = Field(..., gt=0, description="El monto siempre debe ser positivo")
    
    # Origen y destino son opcionales dependiendo del tipo de movimiento
    source_account: Optional[str] = Field(None, description="Ej: Tarjeta Débito, Efectivo")
    destination_account: Optional[str] = Field(None, description="Ej: Cetes, Ahorro Carro")
    category: str
    subcategory: str
    description: str