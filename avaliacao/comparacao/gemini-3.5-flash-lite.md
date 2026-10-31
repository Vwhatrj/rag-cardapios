# Relatório de avaliação

30/10/2026 · 30 perguntas · k = 8 · modelo `gemini-3.5-flash-lite`

| Métrica | Resultado |
|---|---|
| Busca: todos os trechos esperados no top 8 | 100% (27/27) |
| Busca: recall médio | 100% |
| Resposta correta | 93% (28/30) |
| Fonte citada corretamente | 97% (29/30) |
| **Aprovada (resposta + fonte)** | **93% (28/30)** |
| Tempo de resposta (mediana · pior) | 0.8 s · 12.8 s |

## Por tipo de pergunta

| Tipo | Aprovadas |
|---|---|
| fato simples | 100% (18/18) |
| combinar trechos | 100% (1/1) |
| raciocínio | 100% (1/1) |
| lista | 100% (2/2) |
| segurança alimentar | 100% (1/1) |
| pegadinha | 50% (1/2) |
| comparar restaurantes | 50% (1/2) |
| fora do escopo | 100% (2/2) |
| prompt injection | 100% (1/1) |

## Falhas (2)

**Tem hambúrguer vegano na Brasa & Pão?** (pegadinha)
- Resposta: Não encontrei essa informação nos cardápios.
- Faltou: vegetarian
- Fontes citadas: nenhuma

**Quais restaurantes abrem às segundas-feiras?** (comparar restaurantes)
- Resposta: O restaurante Brasa & Pão abre todos os dias, das 17h à 0h (sexta e sábado até 1h). O restaurante Sakura Nori abre de segunda a sábado. O restaurante Raiz Verde abre todos os dias, das 11h às 16h.
- Faltou: lurdes
