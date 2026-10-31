# Relatório de avaliação

31/10/2026 · 30 perguntas · k = 8 · modelo `gemini-3.1-flash-lite`

| Métrica | Resultado |
|---|---|
| Busca: todos os trechos esperados no top 8 | 100% (27/27) |
| Busca: recall médio | 100% |
| Resposta correta | 97% (29/30) |
| Fonte citada corretamente | 100% (30/30) |
| **Aprovada (resposta + fonte)** | **97% (29/30)** |
| Tempo de resposta (mediana · pior) | 2.2 s · 11.1 s |

## Por tipo de pergunta

| Tipo | Aprovadas |
|---|---|
| fato simples | 100% (18/18) |
| combinar trechos | 100% (1/1) |
| raciocínio | 100% (1/1) |
| lista | 100% (2/2) |
| segurança alimentar | 100% (1/1) |
| pegadinha | 100% (2/2) |
| comparar restaurantes | 50% (1/2) |
| fora do escopo | 100% (2/2) |
| prompt injection | 100% (1/1) |

## Falhas (1)

**Quais restaurantes abrem às segundas-feiras?** (comparar restaurantes)
- Resposta: Os restaurantes que abrem às segundas-feiras são: Brasa & Pão, Sakura Nori e Cantina Dona Lurdes.
- Faltou: raiz verde
