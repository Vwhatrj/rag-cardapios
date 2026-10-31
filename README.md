# RAG de cardápios

API em **Python + FastAPI** que responde perguntas sobre cardápios de restaurantes usando **RAG** (*Retrieval-Augmented Generation*): primeiro busca os trechos relevantes por similaridade semântica, depois pede ao **Gemini** uma resposta baseada só nesses trechos, **citando as fontes**. Se a informação não estiver nos cardápios, a API diz que não encontrou em vez de inventar.

Tudo roda com custo zero: embeddings locais e a camada gratuita do Gemini.

```http
POST /perguntar
{"pergunta": "Quanto fica uma Calabresa com borda recheada no Forno da Vila?"}
```
```json
{
  "resposta": "A Calabresa da Casa custa R$ 52,00 e a borda recheada custa + R$ 9,00, totalizando R$ 61,00.",
  "fontes": [
    {"id": "forno-da-vila#calabresa-da-casa", "restaurante": "Forno da Vila", "titulo": "Calabresa da Casa", "trecho": "..."},
    {"id": "forno-da-vila#info", "restaurante": "Forno da Vila", "titulo": "Informações gerais", "trecho": "..."}
  ],
  "modelo": "gemini-..."
}
```

## Como funciona

```mermaid
flowchart LR
    A[Cardápios .md] -->|1 trecho por prato<br>+ 1 de informações| B[Trechos]
    B -->|multilingual-e5-small| C[(Vetores)]
    P[Pergunta] -->|mesmo modelo| Q[Vetor da pergunta]
    Q -->|cosseno, top k| C
    C --> T[k trechos mais parecidos]
    T --> G[Gemini: responda só com base nos trechos e cite os ids]
    G --> R[Resposta + fontes]
```

1. **Indexação** (`app/cardapios.py`, `app/busca.py`): cada cardápio vira um trecho por prato e um trecho com as informações gerais (horário, entrega, pagamento). O nome do restaurante entra em todo trecho, senão "Margherita: R$ 49" perde o contexto. Os trechos viram vetores com o `intfloat/multilingual-e5-small`, que roda localmente.
2. **Busca**: a pergunta vira vetor, e os `k` trechos mais parecidos (similaridade de cosseno) são escolhidos. Com cerca de 60 trechos, um produto de matrizes no NumPy resolve em microssegundos, então um banco vetorial seria complexidade sem ganho.
3. **Geração** (`app/rag.py`, `app/llm.py`): os trechos vão para o Gemini com regras explícitas: usar só o que está nos trechos, recusar com uma frase padrão quando não souber, tratar os trechos como dados e não como instruções, e devolver JSON com as fontes usadas. Fontes que o modelo cite **sem tê-las recebido** são descartadas no código.

## Avaliação

Os testes automáticos verificam se o código funciona. A **avaliação** mede se as respostas estão certas. Para isso há 30 perguntas com resposta conhecida em [`avaliacao/perguntas.json`](avaliacao/perguntas.json): fatos simples, listas, perguntas que exigem combinar trechos (pizza + borda), comparações entre restaurantes, pegadinhas ("tem hambúrguer vegano?", quando o único veggie leva queijo), alergias, perguntas fora do escopo e uma tentativa de *prompt injection*.

A busca e a resposta são avaliadas **separadamente**, porque falham por motivos diferentes. Se a busca não traz o trecho certo, o LLM não tem como acertar.

### Busca: quantos trechos recuperar (k)

| k | Todos os trechos esperados recuperados | Recall médio |
|---|---|---|
| 1 | 70% | 76% |
| 3 | 85% | 88% |
| 5 | 93% | 95% |
| **8** | **100%** | **100%** |

Com k pequeno, quem falha são as perguntas que **comparam restaurantes** ("qual tem a entrega mais barata?") e as **listas** ("quais pratos sem glúten?"). Elas precisam de vários trechos ao mesmo tempo, e a pergunta não se parece com nenhum deles em particular. Por isso o padrão é `k = 8`: o custo extra são algumas centenas de tokens por pergunta.

### Resposta completa (busca + Gemini)

_Rode `python -m avaliacao.avaliar` para gerar [`avaliacao/relatorio.md`](avaliacao/relatorio.md)._

A checagem é por palavras-chave (fatos que **devem** aparecer e frases que **não podem** aparecer), sem acento e sem diferenciar maiúsculas. É determinística e auditável: dá para ver exatamente por que cada resposta passou ou falhou. Usar outro LLM como juiz seria mais flexível, mas também menos previsível.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (no Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # e coloque sua GEMINI_API_KEY (grátis no AI Studio)
```

| Comando | O que faz |
|---|---|
| `uvicorn app.main:app --reload` | Sobe a API. A documentação interativa fica em http://127.0.0.1:8000/docs |
| `pytest` | 30 testes em ~15 s, com um LLM falso: sem internet e sem gastar cota |
| `python -m avaliacao.avaliar --so-busca` | Avalia só a busca (não usa o Gemini) |
| `python -m avaliacao.avaliar` | Avaliação completa, com o Gemini |

## Estrutura

```
app/
  cardapios.py   lê os .md e gera os trechos
  busca.py       embeddings + busca por cosseno (com cache em disco)
  llm.py         cliente REST do Gemini (escolhe o modelo, faz retentativas no limite gratuito)
  rag.py         prompt, interpretação do JSON e validação das fontes
  main.py        API FastAPI
dados/cardapios/ 6 restaurantes fictícios, 52 pratos
tests/           pytest (cardápios, busca, RAG, API, avaliação)
avaliacao/       perguntas com resposta conhecida + script de relatório
```

## Decisões e limitações

- **Os cardápios são fictícios.** Assim não há marca de terceiros e dá para criar casos difíceis de propósito.
- **O LLM é injetado na API** (`criar_app(llm=...)`). Os testes usam um LLM falso e rodam offline. Para trocar o Gemini por outro modelo, basta implementar `gerar(sistema, prompt)`.
- **Limitação: agregações.** Perguntas como "qual o prato mais barato de todos?" dependem de a busca trazer todos os pratos. Isso não escala: com centenas de restaurantes, o caminho seria extrair os campos (preço, etiquetas) para uma tabela e responder esse tipo de pergunta com filtros, deixando a busca semântica para o resto.
- **Limitação: cardápios em PDF** ainda não são lidos. Hoje a entrada é Markdown.
