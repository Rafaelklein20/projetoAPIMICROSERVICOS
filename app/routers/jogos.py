from fastapi import APIRouter, status, Response
from typing import List
from app.schemas import JogoCreate, JogoUpdate, JogoResponse
from app import models
from app.producer import publicar_mensagem  # Função que envia ao RabbitMQ

router = APIRouter(prefix="/jogos", tags=["jogos"])


@router.post("/", response_model=JogoResponse, status_code=status.HTTP_201_CREATED)
async def criar(jogo: JogoCreate):
    novo_jogo = await models.criar_jogo(jogo)
    
  
    publicar_mensagem("fila_auditoria", {
        "evento": "CRIACAO",
        "jogo_id": novo_jogo["id"],
        "dados": novo_jogo
    })
    
   
    publicar_mensagem("fila_notificacoes", {
        "tipo": "NOVO_JOGO",
        "titulo": novo_jogo["titulo"],
        "preco": novo_jogo["preco"]
    })
    
    return novo_jogo



@router.get("/", response_model=List[JogoResponse], status_code=status.HTTP_200_OK)
async def listar():
    return await models.listar_jogos()



@router.get("/{jogo_id}", response_model=JogoResponse, status_code=status.HTTP_200_OK)
async def buscar(jogo_id: str):
    return await models.buscar_jogo_por_id(jogo_id)



@router.put("/{jogo_id}", response_model=JogoResponse, status_code=status.HTTP_200_OK)
async def atualizar(jogo_id: str, jogo: JogoUpdate):
    jogo_atualizado = await models.atualizar_jogo(jogo_id, jogo)
    
   
    publicar_mensagem("fila_auditoria", {
        "evento": "ATUALIZACAO",
        "jogo_id": jogo_id,
        "alteracoes": jogo.model_dump(exclude_unset=True)
    })
    
    return jogo_atualizado



@router.delete("/{jogo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar(jogo_id: str):
    await models.deletar_jogo(jogo_id)
    

    publicar_mensagem("fila_auditoria", {
        "evento": "DELECAO",
        "jogo_id": jogo_id
    })
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)