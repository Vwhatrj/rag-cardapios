"""API HTTP. Rodar com:  uvicorn app.main:app --reload   e abrir http://127.0.0.1:8000/docs"""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.busca import Indice, embedder_e5
from app.cardapios import carregar_trechos
from app.llm import LLM, ErroLLM, Gemini
from app.rag import responder


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500, examples=["Qual pizza vegana tem no Forno da Vila?"])
    k: int = Field(8, ge=1, le=20, description="Quantos trechos buscar antes de chamar o LLM")


class Fonte(BaseModel):
    id: str
    restaurante: str
    titulo: str
    trecho: str


class RespostaAPI(BaseModel):
    resposta: str
    fontes: list[Fonte]
    modelo: str


def criar_app(indice: Indice | None = None, llm: LLM | None = None) -> FastAPI:
    """Fábrica da aplicação. Os testes injetam um índice e um LLM falso; em produção, ambos são criados na subida."""
    estado: dict = {"indice": indice, "llm": llm}

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI):
        load_dotenv()
        if estado["indice"] is None:
            estado["indice"] = Indice(carregar_trechos(), *embedder_e5())
        if estado["llm"] is None:
            estado["llm"] = Gemini()
        yield

    app = FastAPI(
        title="RAG de cardápios",
        description="Responde perguntas sobre cardápios usando busca semântica + Gemini, sempre citando as fontes.",
        version="1.0.0",
        lifespan=ciclo_de_vida,
    )

    @app.get("/saude")
    def saude():
        return {"status": "ok", "trechos": len(estado["indice"].trechos), "modelo": estado["llm"].nome}

    @app.get("/restaurantes")
    def restaurantes():
        nomes = dict.fromkeys(t.restaurante for t in estado["indice"].trechos)
        return {"restaurantes": list(nomes)}

    @app.post("/perguntar", response_model=RespostaAPI)
    def perguntar(corpo: Pergunta):
        try:
            r = responder(corpo.pergunta, estado["indice"], estado["llm"], k=corpo.k)
        except ErroLLM as erro:
            raise HTTPException(status_code=502, detail=str(erro)) from erro
        return RespostaAPI(
            resposta=r.resposta,
            fontes=[Fonte(id=t.id, restaurante=t.restaurante, titulo=t.titulo, trecho=t.texto) for t in r.fontes],
            modelo=estado["llm"].nome,
        )

    return app


app = criar_app()
