#!/usr/bin/env bash
# Vizin — rodar a simulação com Gemini no servidor e enviar ao GitHub
# Versão: v1.1 (2026-11-05)
# Histórico: v1.0 criação (atualiza o código, simula, analisa, grava e envia os resultados). v1.1 modo controle: FICHA=neutra roda as personas sem dores, medos e gatilhos.
#
# Uso (no servidor, dentro da pasta do projeto):
#   ./simulacao/rodar_gemini.sh            # 3 rodadas por persona
#   RODADAS=5 ./simulacao/rodar_gemini.sh  # outro número de rodadas
#   FICHA=neutra ./simulacao/rodar_gemini.sh  # controle: ficha neutra (origem gemini-neutro)
#
# Requisitos já configurados no servidor: arquivo .env (GEMINI_API_KEY e GEMINI_MODEL),
# chave de escrita do GitHub (deploy key) e python3-openpyxl instalado.
set -euo pipefail
cd "$(dirname "$0")/.."

RODADAS="${RODADAS:-3}"
FICHA="${FICHA:-completa}"
if [ "${FICHA}" = "neutra" ]; then ORIGEM="gemini-neutro"; else ORIGEM="gemini"; fi

# Evita duas execuções ao mesmo tempo
exec 9>/tmp/vizin_rodar_gemini.lock
flock -n 9 || { echo "Já existe uma execução em andamento. Saindo."; exit 1; }

[ -f .env ] || { echo "Falta o arquivo .env (GEMINI_API_KEY e GEMINI_MODEL)."; exit 1; }

echo "== 1/4 Atualizando o código =="
git pull --ff-only

echo "== 2/4 Simulando com Gemini (${RODADAS} rodadas por persona) =="
python3 simulacao/simular.py --provedor gemini --rodadas "${RODADAS}" --ficha "${FICHA}"

echo "== 3/4 Analisando =="
python3 simulacao/analisar.py --origem "${ORIGEM}"

echo "== 4/4 Enviando resultados ao GitHub =="
git add resultados
if git diff --cached --quiet; then
  echo "Nada novo para enviar."
else
  MODELO="$(grep -E '^GEMINI_MODEL=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")"
  git commit -q -m "Resultados da simulação com Gemini (${MODELO}), ficha ${FICHA}, ${RODADAS} rodadas por persona"
  git push origin main
fi
echo "== Pronto. O site atualiza sozinho em 1 a 2 minutos. =="
