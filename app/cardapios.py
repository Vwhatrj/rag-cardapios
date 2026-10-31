"""Lê os cardápios em Markdown e os quebra em trechos: um por prato e um com as informações gerais."""
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

PASTA_PADRAO = Path(__file__).resolve().parent.parent / "dados" / "cardapios"


@dataclass(frozen=True)
class Trecho:
    id: str           # ex.: "forno-da-vila#margherita" ou "forno-da-vila#info"
    restaurante: str  # ex.: "Forno da Vila"
    titulo: str       # nome do prato, ou "Informações gerais"
    texto: str        # o que vai para a busca e para o LLM


def slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


@dataclass(frozen=True)
class CardapioLido:
    base: str                                # nome do arquivo sem extensão, prefixo dos ids
    restaurante: str
    tipo: str
    info: list[str]                          # linhas "Chave: valor" das informações gerais
    pratos: list[tuple[str, list[str]]]      # (nome do prato, linhas "Chave: valor")


def ler_markdown(caminho: Path) -> CardapioLido:
    restaurante, tipo = "", ""
    info: list[str] = []
    pratos: list[tuple[str, list[str]]] = []

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha.startswith("# "):
            restaurante = linha[2:].strip()
        elif linha.startswith("## "):
            pratos.append((linha[3:].strip(), []))
        elif linha.startswith("- "):
            campo = linha[2:].strip()
            if pratos:
                pratos[-1][1].append(campo)
            else:
                info.append(campo)
                if campo.lower().startswith("tipo:"):
                    tipo = campo.split(":", 1)[1].strip()

    if not restaurante:
        raise ValueError(f"{caminho.name}: falta o título '# Nome do restaurante'")
    return CardapioLido(caminho.stem, restaurante, tipo, info, pratos)


def ler_cardapio(caminho: Path) -> list[Trecho]:
    c = ler_markdown(caminho)
    # O nome e o tipo do restaurante vão em todo trecho: sem isso, "Margherita: R$ 49" perde o contexto
    cabecalho = f"{c.restaurante} ({c.tipo})" if c.tipo else c.restaurante
    trechos = [Trecho(f"{c.base}#info", c.restaurante, "Informações gerais", f"{cabecalho} — informações gerais\n" + "\n".join(c.info))]
    for nome, campos in c.pratos:
        trechos.append(Trecho(f"{c.base}#{slug(nome)}", c.restaurante, nome, f"{cabecalho} — {nome}\n" + "\n".join(campos)))
    return trechos


def carregar_trechos(pasta: Path = PASTA_PADRAO) -> list[Trecho]:
    trechos = [t for arquivo in sorted(pasta.glob("*.md")) for t in ler_cardapio(arquivo)]
    ids = [t.id for t in trechos]
    repetidos = {i for i in ids if ids.count(i) > 1}
    if repetidos:
        raise ValueError(f"IDs de trecho repetidos: {sorted(repetidos)}")
    return trechos
