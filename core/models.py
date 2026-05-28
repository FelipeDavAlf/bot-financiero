from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date

class Transaction(BaseModel):
    fecha: date
    # Restringimos las opciones para que Gemini no invente tipos de movimiento
    tipo_movimiento: Literal["Ingreso", "Gasto", "Traspaso"]
    monto: float = Field(..., gt=0, description="El monto siempre debe ser positivo")
    
    # Origen y destino son opcionales dependiendo del tipo de movimiento
    cuenta_origen: Optional[str] = Field(None, description="Ej: Tarjeta Débito, Efectivo")
    cuenta_destino: Optional[str] = Field(None, description="Ej: Cetes, Ahorro Carro")
    
    categoria: str
    descripcion: str