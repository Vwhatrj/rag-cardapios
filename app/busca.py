"""Busca semântica: transforma trechos e perguntas em vetores e compara por similaridade de cosseno.

Com ~60 trechos, um produto de matrizes no NumPy resolve em microssegundos; um banco vetorial
(FAISS, Chroma) só começa a compensar com dezenas de milhares de trechos.
"""
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import numpy as np

from app.cardapios import Trecho

MODELO_EMBEDDINGS = "intfloat/multilingual-e5-small"
CACHE_PADRAO = Path(__file__).resolve().parent.parent / "dados" / "indice_cache.npz"

# Recebe textos e devolve uma matriz (n, d) de vetores normalizados
Embedder = Callable[[list[str]], np.ndarray]


def embedder_e5(nome: str = MODELO_EMBEDDINGS) -> tuple[Embedder, Embedder]:
    """Devolve (embed_trechos, embed_perguntas). O E5 foi treinado com os prefixos 'passage:' e 'query:'."""
    from sentence_transformers import SentenceTransformer

    modelo = SentenceTransformer(nome)

    def codificar(prefixo: str) -> Embedder:
        return lambda textos: modelo.encode([prefixo + t for t in textos], normalize_embeddings=True)

    return codificar("passage: "), codificar("query: ")


class Indice:
    def __init__(self, trechos: list[Trecho], embed_trechos: Embedder, embed_perguntas: Embedder,
                 cache: Path | None = CACHE_PADRAO):
        self.trechos = trechos
        self._embed_pergunta = embed_perguntas
        self.vetores = self._vetores(trechos, embed_trechos, cache)

    @staticmethod
    def _vetores(trechos: list[Trecho], embed: Embedder, cache: Path | None) -> np.ndarray:
        # O cache só vale se os textos forem exatamente os mesmos (qualquer edição no cardápio reindexa)
        assinatura = hashlib.sha256(json.dumps([MODELO_EMBEDDINGS] + [t.texto for t in trechos]).encode()).hexdigest()
        if cache and cache.exists():
            salvo = np.load(cache)
            if str(salvo["assinatura"]) == assinatura:
                return salvo["vetores"]
        vetores = np.asarray(embed([t.texto for t in trechos]), dtype=np.float32)
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez(cache, vetores=vetores, assinatura=assinatura)
        return vetores

    def buscar(self, pergunta: str, k: int = 8) -> list[tuple[Trecho, float]]:
        consulta = np.asarray(self._embed_pergunta([pergunta]), dtype=np.float32)[0]
        notas = self.vetores @ consulta  # vetores normalizados: produto escalar = cosseno
        melhores = np.argsort(-notas)[:k]
        return [(self.trechos[i], float(notas[i])) for i in melhores]
