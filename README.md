# Vizin — Pesquisa sintética em Tangará da Serra (MT)

**Versão v1.6 — 2026-11-04**

| Versão | Data | Mudança |
|---|---|---|
| v1.0 | 2026-11-04 | Criação: 15 personas, questionários estruturados, simulador e analisador. |
| v1.1 | 2026-11-04 | Entrevistas isoladas feitas pelo Claude (pasta `simulacao_claude/`), importador e análise separada por modelo. |
| v1.2 | 2026-11-04 | Site estático (pasta `site/`) com metodologia, personas, resultados, entrevistas e comparação sintético × real; montagem automática para o Vercel. |
| v1.3 | 2026-11-04 | Nova home (plataforma de validação prévia, duas ferramentas), página Cenário multiagente (simulação qualitativa do Victor Hugo Borsato Xavier), folder ilustrativo e créditos da equipe. |
| v1.4 | 2026-11-04 | Resultados da simulação com Gemini (`gemini-3.5-flash-lite`), página de comparação Claude × Gemini e script `simulacao/rodar_gemini.sh` (simula, analisa e envia ao GitHub a partir do servidor). |
| v1.5 | 2026-11-04 | Visual acadêmico (paleta azul-marinho e cinza, títulos serifados), hero na home e diagrama do processo na Metodologia. |
| v1.6 | 2026-11-04 | Logotipo da UNEMAT no topo da home, brasão e aviso de trabalho acadêmico no rodapé, faixa de título azul-marinho em todas as páginas internas. |

Projeto da pós-graduação em Gestão e Inovação (UNEMAT). Este repositório reúne o método, o código e os dados
da **simulação com personas sintéticas** usada para explorar hipóteses sobre o Vizin antes do piloto com lojas reais.

## O que isto é e o que não é

* É uma **exploração de hipóteses e mapeamento de atritos** de adoção.
* **Não** é pesquisa de mercado e **não** mede a demanda real. Respostas de IA tendem a ser mais favoráveis do que as de pessoas reais.
* Por isso o método inclui: personas com a fonte de cada premissa, alternativas negativas permitidas, três rodadas por persona
  (para medir estabilidade), alarme anti-viés (acima de 80% de adesão) e comparação posterior com as respostas reais.

## Como funciona

1. `dados/personas.json`: 6 lojistas e 9 consumidores fictícios (moda, calçados e acessórios).
2. `dados/questionario_*.json`: os questionários do grupo, com o texto original das perguntas.
3. `simulacao/simular.py`: cada persona responde sozinha ao questionário (JSON validado, com justificativa curta).
4. `simulacao/analisar.py`: gera `resultados/resumo.json`, CSVs e o Excel com gráficos.

## Como rodar (no servidor Linux)

Todos os comandos abaixo são colados **no terminal conectado ao servidor** (SSH), dentro da pasta do projeto.

Instalar o necessário para o Excel (uma vez só):

```bash
sudo apt install -y python3-openpyxl
```

Criar o arquivo de chaves e preencher (a chave fica só no servidor):

```bash
cp .env.example .env && chmod 600 .env && nano .env
```

Testar o programa sem gastar nada (respostas aleatórias; **nunca** vira resultado):

```bash
python3 simulacao/simular.py --mock --rodadas 1
```

Rodar de verdade (use `--provedor gemini` se for a chave gratuita do Google):

```bash
python3 simulacao/simular.py --provedor anthropic --rodadas 3
python3 simulacao/analisar.py
```

Se a execução parar no meio, rode o mesmo comando de novo: ele continua de onde parou.

## Segurança

* O arquivo `.env` (chaves) está no `.gitignore` e nunca deve ser enviado ao GitHub.
* Respostas reais de participantes (pasta `dados_reais/`) também ficam fora do repositório. Só dados agregados e anônimos podem ser publicados.
* O servidor só faz conexões de saída; nenhuma porta é aberta.

## Site (Vercel)

O site fica na pasta `site/` e é estático (sem dependências). A cada envio ao GitHub, o Vercel roda
`node scripts/montar_site.js`, que copia os dados para `site/data/` (nunca inclui dados de teste) e publica.

Para ver no computador (opcional):

```bash
node scripts/montar_site.js
cd site && python3 -m http.server 8000
```

Depois abra `http://localhost:8000` no navegador.

Páginas: Início, Metodologia, Personas, Resultados, Entrevistas e Sintético × Real (o CSV com respostas reais é lido
só no navegador e nunca é enviado a servidor algum).


## Rodar a simulação com Gemini no servidor (v1.4)

Pré-requisitos no servidor: `.env` com `GEMINI_API_KEY` e `GEMINI_MODEL` (o `.env` nunca vai para o GitHub),
chave de escrita do GitHub (*deploy key*) e `python3-openpyxl` instalado.

```
cd ~/vizin-pesquisa
./simulacao/rodar_gemini.sh
```

O script atualiza o código, simula (3 rodadas por persona, retomando de onde parou), analisa e envia `resultados/` ao GitHub.
O site publica sozinho em 1 a 2 minutos. Limites do plano gratuito mudam: confira o modelo e os limites diários no Google AI Studio.
