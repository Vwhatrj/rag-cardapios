# Relatório de avaliação

31/10/2026 · conjunto **agregacao** · 11 perguntas · modo **agente** · modelo `gemini-3.1-flash-lite`

| Métrica | Resultado |
|---|---|
| Resposta correta | 91% (10/11) |
| Fonte citada corretamente | 91% (10/11) |
| **Aprovada (resposta + fonte)** | **91% (10/11)** |
| Tempo de resposta (mediana · pior) | 9.6 s · 11.5 s |
| Chamadas ao LLM por pergunta (média · máx) | 2.0 · 2 |
| Tokens por pergunta (média: entrada + saída) | 2.547 + 150 |
| Refeitas por erro do Gemini · ainda com erro | 0 · 0 |

## Por tipo de pergunta

| Tipo | Aprovadas |
|---|---|
| mais barato | 100% (3/3) |
| mais caro | 100% (1/1) |
| lista completa | 100% (3/3) |
| contagem | 100% (2/2) |
| lista vazia | 0% (0/1) |
| comparar restaurantes | 100% (1/1) |

## Falhas (1)

**Tenho intolerância a lactose: quais hambúrgueres da Brasa & Pão posso pedir?** (lista vazia)
- Ferramentas: filtrar_pratos({"restaurante": "Brasa & Pão", "sem_alergenicos": ["lactose"], "categoria": "hambúrguer"})
- Resposta: Não encontrei hambúrgueres sem lactose no restaurante Brasa & Pão.
- Faltou: nenhum
- Continha o proibido: nao encontrei
- Fontes citadas: nenhuma
