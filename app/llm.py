"""Cliente mínimo do Google Gemini (camada gratuita do AI Studio) via API REST."""
import os
import re
import time
from typing import Protocol

import httpx

API = "https://generativelanguage.googleapis.com/v1beta"


class LLM(Protocol):
    nome: str

    def gerar(self, sistema: str, prompt: str) -> str: ...


class ErroLLM(RuntimeError):
    pass


def escolher_modelo(ids: list[str]) -> str:
    """Prefere o 'flash' estável mais recente: bom equilíbrio entre qualidade e limite gratuito."""
    def versao(i: str) -> float:
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", i)
        return float(m.group(1)) if m else 0.0

    estaveis = [i for i in ids if "flash" in i and not re.search(r"lite|preview|exp|8b|tts|image|audio|live", i)]
    candidatos = estaveis or [i for i in ids if "flash" in i] or ids
    if not candidatos:
        raise ErroLLM("Nenhum modelo Gemini disponível para esta chave.")
    return max(candidatos, key=versao)


class Gemini:
    def __init__(self, chave: str | None = None, modelo: str | None = None, timeout: float = 60):
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
        return escolher_modelo(ids)

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
        # A camada gratuita tem limite de pedidos por minuto: em 429/503, espera e tenta de novo
        for tentativa in range(tentativas):
            r = self._http.post(url, json=corpo)
            if r.status_code not in (429, 503) or tentativa == tentativas - 1:
                return r
            time.sleep(min(60, 5 * 2 ** tentativa))
        return r

    @staticmethod
    def _checar(r: httpx.Response) -> None:
        if r.is_success:
            return
        try:
            msg = r.json()["error"]["message"]
        except Exception:
            msg = r.text[:300]
        raise ErroLLM(f"Gemini respondeu {r.status_code}: {msg}")
