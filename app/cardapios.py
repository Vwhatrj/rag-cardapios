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


def ler_cardapio(caminho: Path) -> list[Trecho]:
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

    base = caminho.stem
    # O nome e o tipo do restaurante vão em todo trecho: sem isso, "Margherita: R$ 49" perde o contexto
    cabecalho = f"{restaurante} ({tipo})" if tipo else restaurante
    trechos = [Trecho(f"{base}#info", restaurante, "Informações gerais", f"{cabecalho} — informações gerais\n" + "\n".join(info))]
    for nome, campos in pratos:
        trechos.append(Trecho(f"{base}#{slug(nome)}", restaurante, nome, f"{cabecalho} — {nome}\n" + "\n".join(campos)))
    return trechos


def carregar_trechos(pasta: Path = PASTA_PADRAO) -> list[Trecho]:
    trechos = [t for arquivo in sorted(pasta.glob("*.md")) for t in ler_cardapio(arquivo)]
    ids = [t.id for t in trechos]
    repetidos = {i for i in ids if ids.count(i) > 1}
    if repetidos:
        raise ValueError(f"IDs de trecho repetidos: {sorted(repetidos)}")
    return trechos
