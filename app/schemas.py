from pydantic import BaseModel, Field
from typing import Optional

class JogoBase(BaseModel):
    titulo: str = Field(..., example="The Witcher 3")
    genero: str = Field(..., example="RPG")
    plataforma: str = Field(..., example="PC")
    ano_lancamento: int = Field(..., example=2015)
    preco: float = Field(..., example=79.90)

class JogoCreate(JogoBase):
    pass

class JogoUpdate(BaseModel):
    titulo: Optional[str] = Field(None, example="The Witcher 3: Wild Hunt")
    genero: Optional[str] = Field(None, example="RPG de Acao")
    plataforma: Optional[str] = Field(None, example="PC")
    ano_lancamento: Optional[int] = Field(None, example=2015)
    preco: Optional[float] = Field(None, example=99.90)

class JogoResponse(JogoBase):
    id: str
    class Config:
        from_attributes = True