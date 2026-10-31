"""API HTTP. Rodar com:  uvicorn app.main:app --reload   e abrir http://127.0.0.1:8000/docs"""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import agente
from app.busca import Indice, embedder_e5
from app.cardapios import carregar_trechos
from app.catalogo import carregar_catalogo
from app.ferramentas import Ferramentas
from app.llm import ErroLLM, Gemini, LLMComFerramentas
from app.rag import responder


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500, examples=["Qual pizza vegana tem no Forno da Vila?"])
    k: int = Field(8, ge=1, le=20, description="Quantos trechos buscar antes de chamar o LLM")


class PerguntaAgente(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500, examples=["Qual a sobremesa mais barata entre todos os restaurantes?"])


class Fonte(BaseModel):
    id: str
    restaurante: str
    titulo: str
    trecho: str


class RespostaAPI(BaseModel):
    resposta: str
    fontes: list[Fonte]
    modelo: str


class PassoAPI(BaseModel):
    ferramenta: str
    argumentos: dict
    resultados: int


class RespostaAgenteAPI(RespostaAPI):
    passos: list[PassoAPI] = Field(description="As ferramentas que o agente chamou, na ordem")
    chamadas_llm: int = Field(description="Quantas vezes o modelo foi chamado para chegar à resposta")


def criar_app(indice: Indice | None = None, llm: LLMComFerramentas | None = None) -> FastAPI:
    """Fábrica da aplicação. Os testes injetam um índice e um LLM falso; em produção, ambos são criados na subida."""
    estado: dict = {"indice": indice, "llm": llm, "ferramentas": None}

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI):
        load_dotenv()
        if estado["indice"] is None:
            estado["indice"] = Indice(carregar_trechos(), *embedder_e5())
        if estado["llm"] is None:
            estado["llm"] = Gemini()
        estado["ferramentas"] = Ferramentas(*carregar_catalogo(), estado["indice"])
        estado["trecho_por_id"] = {t.id: t for t in estado["indice"].trechos}
        yield

    app = FastAPI(
        title="RAG de cardápios",
        description=(
            "Responde perguntas sobre cardápios citando as fontes. `/perguntar`: RAG simples (busca semântica + "
            "Gemini). `/agente`: o Gemini decide quais ferramentas chamar (filtro exato, busca, informações)."
        ),
        version="1.1.0",
        lifespan=ciclo_de_vida,
    )

    def fonte(id_: str) -> Fonte:
        t = estado["trecho_por_id"][id_]
        return Fonte(id=t.id, restaurante=t.restaurante, titulo=t.titulo, trecho=t.texto)

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
        return RespostaAPI(resposta=r.resposta, fontes=[fonte(t.id) for t in r.fontes], modelo=estado["llm"].nome)

    @app.post("/agente", response_model=RespostaAgenteAPI)
    def perguntar_ao_agente(corpo: PerguntaAgente):
        try:
            r = agente.responder(corpo.pergunta, estado["ferramentas"], estado["llm"])
        except ErroLLM as erro:
            raise HTTPException(status_code=502, detail=str(erro)) from erro
        return RespostaAgenteAPI(
            resposta=r.resposta,
            fontes=[fonte(i) for i in r.fontes],
            modelo=estado["llm"].nome,
            passos=[PassoAPI(ferramenta=p.ferramenta, argumentos=p.argumentos, resultados=p.resultados) for p in r.passos],
            chamadas_llm=r.chamadas_llm,
        )

    return app


app = criar_app()
