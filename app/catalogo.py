"""Os mesmos cardápios, lidos como tabela: preço em número, etiquetas e alergênicos em lista.

A busca semântica é boa para "algo parecido com X", mas não para "o mais barato" ou "todos os que":
para isso, filtrar uma tabela é exato e barato.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from app.cardapios import PASTA_PADRAO, ler_markdown, slug


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def _radical(texto: str) -> str:
    # "vegano"/"vegana" e "vegetariano"/"vegetariana" viram o mesmo radical
    return normalizar(texto).rstrip("ao").rstrip("s")


def _campos(linhas: list[str]) -> dict[str, str]:
    campos = {}
    for linha in linhas:
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            campos[normalizar(chave)] = valor.strip()
    return campos


def _lista(valor: str | None) -> list[str]:
    return [v.strip() for v in (valor or "").split(",") if v.strip()]


def _preco(texto: str) -> float | None:
    m = re.search(r"R\$\s*(\d+(?:\.\d{3})*,\d{2})", texto)
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


@dataclass(frozen=True)
class Prato:
    id: str
    restaurante: str
    nome: str
    categoria: str
    preco: float | None        # o primeiro preço do texto (ex.: a feijoada individual)
    preco_texto: str           # o texto original, que pode ter variações ("ou R$ 82,00 para 2")
    descricao: str
    etiquetas: list[str] = field(default_factory=list)
    alergenicos: list[str] = field(default_factory=list)

    def resumo(self) -> dict:
        return {"id": self.id, "restaurante": self.restaurante, "prato": self.nome, "categoria": self.categoria,
                "preco": self.preco_texto, "etiquetas": self.etiquetas, "alergenicos": self.alergenicos}


@dataclass(frozen=True)
class Restaurante:
    id: str
    nome: str
    informacoes: dict[str, str]


def carregar_catalogo(pasta: Path = PASTA_PADRAO) -> tuple[list[Prato], list[Restaurante]]:
    pratos, restaurantes = [], []
    for arquivo in sorted(pasta.glob("*.md")):
        c = ler_markdown(arquivo)
        info = _campos(c.info)
        restaurantes.append(Restaurante(f"{c.base}#info", c.restaurante, info))
        for nome, linhas in c.pratos:
            campos = _campos(linhas)
            pratos.append(Prato(
                id=f"{c.base}#{slug(nome)}",
                restaurante=c.restaurante,
                nome=nome,
                categoria=campos.get("categoria", ""),
                preco=_preco(campos.get("preco", "")),
                preco_texto=campos.get("preco", ""),
                descricao=campos.get("descricao", ""),
                etiquetas=_lista(campos.get("etiquetas")),
                alergenicos=_lista(campos.get("alergenicos")),
            ))
    return pratos, restaurantes


def filtrar(pratos: list[Prato], *, preco_max: float | None = None, preco_min: float | None = None,
            etiquetas: list[str] | None = None, sem_alergenicos: list[str] | None = None,
            categoria: str | None = None, restaurante: str | None = None,
            ordenar_por: str = "preco", decrescente: bool = False) -> list[Prato]:
    resultado = []
    for p in pratos:
        if preco_max is not None and (p.preco is None or p.preco > preco_max):
            continue
        if preco_min is not None and (p.preco is None or p.preco < preco_min):
            continue
        if etiquetas and not all(any(_radical(e) == _radical(t) for t in p.etiquetas) for e in etiquetas):
            continue
        # Conservador: "pode conter glúten na farofa" também exclui quem pediu sem glúten
        if sem_alergenicos and any(_radical(a) in normalizar(" ".join(p.alergenicos)) for a in sem_alergenicos):
            continue
        if categoria and normalizar(categoria) not in normalizar(p.categoria):
            continue
        if restaurante and normalizar(restaurante) not in normalizar(p.restaurante):
            continue
        resultado.append(p)
    if ordenar_por == "preco":  # pratos sem preço vão para o fim nos dois sentidos
        com_preco = sorted((p for p in resultado if p.preco is not None), key=lambda p: p.preco, reverse=decrescente)
        resultado = com_preco + [p for p in resultado if p.preco is None]
    elif ordenar_por == "nome":
        resultado.sort(key=lambda p: normalizar(p.nome), reverse=decrescente)
    return resultado
