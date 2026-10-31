# Relatório de avaliação

31/10/2026 · conjunto **principal** · 30 perguntas · modo **agente** · modelo `gemini-3.1-flash-lite`

| Métrica | Resultado |
|---|---|
| Resposta correta | 97% (29/30) |
| Fonte citada corretamente | 97% (29/30) |
| **Aprovada (resposta + fonte)** | **97% (29/30)** |
| Tempo de resposta (mediana · pior) | 6.9 s · 46.7 s |
| Chamadas ao LLM por pergunta (média · máx) | 2.0 · 3 |
| Tokens por pergunta (média: entrada + saída) | 2.345 + 75 |
| Refeitas por erro do Gemini · ainda com erro | 3 · 0 |

## Por tipo de pergunta

| Tipo | Aprovadas |
|---|---|
| fato simples | 100% (18/18) |
| combinar trechos | 100% (1/1) |
| raciocínio | 100% (1/1) |
| lista | 100% (2/2) |
| segurança alimentar | 100% (1/1) |
| pegadinha | 50% (1/2) |
| comparar restaurantes | 100% (2/2) |
| fora do escopo | 100% (2/2) |
| prompt injection | 100% (1/1) |

## Falhas (1)

**Tem hambúrguer vegano na Brasa & Pão?** (pegadinha)
- Ferramentas: filtrar_pratos({"restaurante": "Brasa & Pão", "etiquetas": ["vegana"]})
- Resposta: Não, não há hambúrgueres veganos no restaurante Brasa & Pão.
- Faltou: vegetarian
- Fontes citadas: nenhuma
