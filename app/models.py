from bson import ObjectId
from fastapi import status
from app.db import get_database
from app.schemas import JogoCreate, JogoUpdate
from app.errors import ApiError

def fix_id(jogo):
    if jogo:
        jogo["id"] = str(jogo["_id"])
        del jogo["_id"]
    return jogo

async def criar_jogo(jogo: JogoCreate) -> dict:
    db = get_database()
    novo_jogo = jogo.model_dump()
    resultado = await db["jogos"].insert_one(novo_jogo)
    jogo_criado = await db["jogos"].find_one({"_id": resultado.inserted_id})
    return fix_id(jogo_criado)

async def listar_jogos() -> list:
    db = get_database()
    jogos = []
    cursor = db["jogos"].find()
    async for document in cursor:
        jogos.append(fix_id(document))
    return jogos

async def buscar_jogo_por_id(jogo_id: str) -> dict:
    if not ObjectId.is_valid(jogo_id):
        raise ApiError("ID invalido", status_code=status.HTTP_400_BAD_REQUEST)
    
    db = get_database()
    jogo = await db["jogos"].find_one({"_id": ObjectId(jogo_id)})
    if not jogo:
        raise ApiError("Jogo nao encontrado", status_code=status.HTTP_404_NOT_FOUND)
    return fix_id(jogo)

async def atualizar_jogo(jogo_id: str, jogo_data: JogoUpdate) -> dict:
    if not ObjectId.is_valid(jogo_id):
        raise ApiError("ID invalido", status_code=status.HTTP_400_BAD_REQUEST)
    
    db = get_database()
    dados_atualizacao = {k: v for k, v in jogo_data.model_dump().items() if v is not None}
    
    if not dados_atualizacao:
        raise ApiError("Nenhum dado informado para atualizacao", status_code=status.HTTP_400_BAD_REQUEST)
    
    resultado = await db["jogos"].update_one(
        {"_id": ObjectId(jogo_id)},
        {"$set": dados_atualizacao}
    )
    
    if resultado.matched_count == 0:
        raise ApiError("Jogo nao encontrado", status_code=status.HTTP_404_NOT_FOUND)
        
    jogo_atualizado = await db["jogos"].find_one({"_id": ObjectId(jogo_id)})
    return fix_id(jogo_atualizado)

async def deletar_jogo(jogo_id: str) -> bool:
    if not ObjectId.is_valid(jogo_id):
        raise ApiError("ID invalido", status_code=status.HTTP_400_BAD_REQUEST)
        
    db = get_database()
    resultado = await db["jogos"].delete_one({"_id": ObjectId(jogo_id)})
    if resultado.deleted_count == 0:
        raise ApiError("Jogo nao encontrado", status_code=status.HTTP_404_NOT_FOUND)
    return True