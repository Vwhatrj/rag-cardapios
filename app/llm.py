"""Cliente mínimo do Google Gemini (camada gratuita do AI Studio) via API REST."""
import os
import re
import time
from typing import Protocol

import httpx

API = "https://generativelanguage.googleapis.com/v1beta"
# Modelo validado pela avaliação (avaliacao/comparacao). "Mais novo" não é "melhor": o 3.5-flash-lite
# acertou menos que o 3.1. Trocar este valor só depois de rodar a avaliação com o novo modelo.
MODELO_AVALIADO = "gemini-3.1-flash-lite"


class LLM(Protocol):
    nome: str

    def gerar(self, sistema: str, prompt: str) -> str: ...


class ErroLLM(RuntimeError):
    pass


class CotaDiariaEsgotada(ErroLLM):
    """Limite diário da camada gratuita: tentar de novo só volta a funcionar no dia seguinte."""


def escolher_modelo(ids: list[str]) -> str:
    """Prefere o 'flash-lite' estável mais recente, depois o 'flash' estável.

    Para responder com base em trechos já recuperados, o lite acertou o mesmo que os maiores na
    avaliação e respondeu em ~2 s, contra ~30 s do flash mais novo (que não desliga o raciocínio).
    """
    def versao(i: str) -> float:
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", i)
        return float(m.group(1)) if m else 0.0

    estaveis = [i for i in ids if re.fullmatch(r"gemini-\d+(\.\d+)?-flash(-lite)?", i)]
    lites = [i for i in estaveis if i.endswith("-lite")]
    candidatos = lites or estaveis or [i for i in ids if "flash" in i] or ids
    if not candidatos:
        raise ErroLLM("Nenhum modelo Gemini disponível para esta chave.")
    return max(candidatos, key=versao)


class Gemini:
    def __init__(self, chave: str | None = None, modelo: str | None = None, timeout: float | None = None):
        timeout = timeout or float(os.environ.get("GEMINI_TIMEOUT", 60))
        self.chave = chave or os.environ.get("GEMINI_API_KEY", "")
        if not self.chave:
            raise ErroLLM("Defina GEMINI_API_KEY no arquivo .env (chave gratuita em https://aistudio.google.com/apikey).")
        # Chave no cabeçalho, não na URL: assim ela não aparece em logs de requisição
        self._http = httpx.Client(timeout=timeout, headers={"x-goog-api-key": self.chave})
        self.nome = modelo or os.environ.get("GEMINI_MODEL") or self._modelo_padrao()
        self._pensamento: dict | None = None
        self._pensamento_definido = False

    def _modelo_padrao(self) -> str:
        r = self._http.get(f"{API}/models", params={"pageSize": 200})
        self._checar(r)
        ids = [m["name"].removeprefix("models/") for m in r.json().get("models", [])
               if "generateContent" in m.get("supportedGenerationMethods", []) and "gemini" in m["name"]]
        # Se o modelo avaliado for aposentado, escolhe outro em vez de quebrar
        return MODELO_AVALIADO if MODELO_AVALIADO in ids else escolher_modelo(ids)

    def _opcoes_pensamento(self) -> list[dict | None]:
        # Os Flash recentes "pensam" antes de responder; para consultar cardápio isso só deixa mais lento
        if self._pensamento_definido:
            return [self._pensamento]
        if "gemini-2.5" in self.nome:
            return [{"thinkingBudget": 0}, {"thinkingBudget": 128}, None]
        if re.search(r"gemini-[3-9]", self.nome):
            return [{"thinkingLevel": "minimal"}, {"thinkingLevel": "low"}, None]
        return [None]

    def gerar(self, sistema: str, prompt: str) -> str:
        opcoes = self._opcoes_pensamento()
        for i, pensamento in enumerate(opcoes):
            config = {"temperature": 0.1, "responseMimeType": "application/json"}
            if pensamento:
                config["thinkingConfig"] = pensamento
            corpo = {
                "systemInstruction": {"parts": [{"text": sistema}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": config,
            }
            r = self._post_com_retentativa(f"{API}/models/{self.nome}:generateContent", corpo)
            if r.status_code == 400 and pensamento and i < len(opcoes) - 1:
                continue  # este modelo não aceita esse parâmetro de raciocínio
            self._pensamento, self._pensamento_definido = pensamento, True
            break
        self._checar(r)
        candidato = (r.json().get("candidates") or [{}])[0]
        texto = "".join(p.get("text", "") for p in candidato.get("content", {}).get("parts", []) if not p.get("thought"))
        if not texto:
            raise ErroLLM(f"O Gemini não devolveu texto (motivo: {candidato.get('finishReason', 'desconhecido')}).")
        return texto

    def _post_com_retentativa(self, url: str, corpo: dict, tentativas: int = 4) -> httpx.Response:
        # A camada gratuita tem limite por minuto e às vezes demora ou cai: em 429/503 ou timeout, espera e tenta de novo
        for tentativa in range(tentativas):
            ultima = tentativa == tentativas - 1
            try:
                r = self._http.post(url, json=corpo)
            except httpx.TransportError as erro:  # timeout, conexão recusada, DNS...
                if ultima:
                    raise ErroLLM(f"Sem resposta do Gemini após {tentativas} tentativas ({type(erro).__name__}).") from erro
            else:
                if r.status_code not in (429, 503) or ultima or _cota_diaria(r):
                    return r
            time.sleep(min(60, 5 * 2 ** tentativa))
        raise AssertionError("inalcançável")

    @staticmethod
    def _checar(r: httpx.Response) -> None:
        if r.is_success:
            return
        try:
            msg = r.json()["error"]["message"]
        except Exception:
            msg = r.text[:300]
        if _cota_diaria(r):
            raise CotaDiariaEsgotada(f"Cota diária gratuita do modelo esgotada. {msg}")
        raise ErroLLM(f"Gemini respondeu {r.status_code}: {msg}")


def _cota_diaria(r: httpx.Response) -> bool:
    return r.status_code == 429 and "per day" in r.text.lower()
