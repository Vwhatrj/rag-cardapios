# Relatório de avaliação

31/10/2026 · conjunto **agregacao** · 11 perguntas · modo **rag** · modelo `gemini-3.1-flash-lite`

| Métrica | Resultado |
|---|---|
| Busca: todos os trechos esperados no top 8 | 36% (4/11) |
| Busca: recall médio | 66% |
| Resposta correta | 27% (3/11) |
| Fonte citada corretamente | 82% (9/11) |
| **Aprovada (resposta + fonte)** | **27% (3/11)** |
| Tempo de resposta (mediana · pior) | 6.6 s · 58.5 s |
| Chamadas ao LLM por pergunta (média · máx) | 1.0 · 1 |
| Tokens por pergunta (média: entrada + saída) | 1.122 + 87 |
| Refeitas por erro do Gemini · ainda com erro | 1 · 0 |

## Por tipo de pergunta

| Tipo | Aprovadas |
|---|---|
| mais barato | 67% (2/3) |
| mais caro | 100% (1/1) |
| lista completa | 0% (0/3) |
| contagem | 0% (0/2) |
| lista vazia | 0% (0/1) |
| comparar restaurantes | 0% (0/1) |

## Falhas (8)

**Qual a sobremesa mais barata entre todos os restaurantes?** (mais barato)
- Busca não trouxe todos os trechos esperados. Recuperados: brasa-e-pao#frango-crispy, cantina-dona-lurdes#omelete-de-queijo-e-espinafre, brasa-e-pao#classico, brasa-e-pao#duplo-smash, brasa-e-pao#bacon-supremo, brasa-e-pao#milkshake-de-ovomaltine, sakura-nori#yakisoba-de-legumes, brasa-e-pao#info
- Resposta: A sobremesa mais barata é o Milkshake de Ovomaltine, do restaurante Brasa & Pão, por R$ 24,00.
- Faltou: pudim, 10
- Fontes citadas: brasa-e-pao#milkshake-de-ovomaltine

**Quais itens custam menos de R$ 15?** (lista completa)
- Busca não trouxe todos os trechos esperados. Recuperados: cantina-dona-lurdes#omelete-de-queijo-e-espinafre, cantina-dona-lurdes#frango-grelhado-com-legumes, brasa-e-pao#combo-kids, sakura-nori#mochi-de-morango, cantina-dona-lurdes#suco-natural, brasa-e-pao#classico, doce-atelie#pao-de-queijo-porcao-com-6, cantina-dona-lurdes#peixe-a-delicia
- Resposta: O único item que custa menos de R$ 15,00 é o Suco Natural da Cantina Dona Lurdes, que custa R$ 9,00.
- Faltou: espresso, refrigerante, pudim, cappuccino, kombucha, missoshiru

**Quantos itens veganos existem somando todos os restaurantes?** (contagem)
- Busca não trouxe todos os trechos esperados. Recuperados: raiz-verde#info, raiz-verde#salada-tropical, raiz-verde#hamburguer-de-feijao-preto, raiz-verde#moqueca-de-banana-da-terra, raiz-verde#prato-do-dia, raiz-verde#kombucha-da-casa, sakura-nori#yakisoba-de-legumes, raiz-verde#lasanha-de-berinjela
- Resposta: Existem 7 itens veganos listados nos cardápios: Salada Tropical, Hambúrguer de Feijão-Preto, Moqueca de Banana-da-Terra, Prato do Dia, Kombucha da Casa e Lasanha de Berinjela no Raiz Verde, além do Yakisoba de Legumes no Sakura Nori.
- Faltou: 15

**Quais pratos sem glúten custam até R$ 30?** (lista completa)
- Busca não trouxe todos os trechos esperados. Recuperados: cantina-dona-lurdes#bife-acebolado, cantina-dona-lurdes#frango-grelhado-com-legumes, cantina-dona-lurdes#omelete-de-queijo-e-espinafre, cantina-dona-lurdes#feijoada-completa, sakura-nori#mochi-de-morango, brasa-e-pao#classico, cantina-dona-lurdes#peixe-a-delicia, cantina-dona-lurdes#pudim-de-leite
- Resposta: Os pratos sem glúten que custam até R$ 30 são: Frango Grelhado com Legumes (R$ 28,00) e Omelete de Queijo e Espinafre (R$ 25,00) na Cantina Dona Lurdes, e Mochi de Morango (R$ 18,00) no Sakura Nori.
- Faltou: pudim, salada tropical, pao de queijo

**Tenho intolerância a lactose: quais hambúrgueres da Brasa & Pão posso pedir?** (lista vazia)
- Resposta: Não encontrei essa informação nos cardápios.
- Faltou: nenhum
- Continha o proibido: nao encontrei
- Fontes citadas: nenhuma

**Quais restaurantes aceitam vale-refeição?** (comparar restaurantes)
- Busca não trouxe todos os trechos esperados. Recuperados: forno-da-vila#info, sakura-nori#info, raiz-verde#info, sakura-nori#mochi-de-morango, forno-da-vila#refrigerante-lata, sakura-nori#rodizio-completo, forno-da-vila#calabresa-da-casa, sakura-nori#hot-roll-crocante-10-pecas
- Resposta: Os restaurantes que aceitam vale-refeição são o Sakura Nori e o Raiz Verde.
- Faltou: lurdes

**Quais são todos os pratos picantes?** (lista completa)
- Busca não trouxe todos os trechos esperados. Recuperados: brasa-e-pao#frango-crispy, forno-da-vila#diavola, sakura-nori#hot-roll-crocante-10-pecas, cantina-dona-lurdes#peixe-a-delicia, cantina-dona-lurdes#omelete-de-queijo-e-espinafre, cantina-dona-lurdes#frango-grelhado-com-legumes, sakura-nori#yakisoba-de-legumes, cantina-dona-lurdes#feijoada-completa
- Resposta: Os pratos picantes são: Frango Crispy do Brasa & Pão e Diavola do Forno da Vila.
- Faltou: ceviche

**Quantos restaurantes fazem entrega?** (contagem)
- Busca não trouxe todos os trechos esperados. Recuperados: sakura-nori#info, brasa-e-pao#info, cantina-dona-lurdes#info, sakura-nori#combinado-sakura-20-pecas, doce-atelie#info, sakura-nori#rodizio-completo, sakura-nori#hot-roll-crocante-10-pecas, raiz-verde#info
- Resposta: Quatro restaurantes fazem entrega: Sakura Nori, Brasa & Pão, Cantina Dona Lurdes e Doce Ateliê.
- Faltou: 5
