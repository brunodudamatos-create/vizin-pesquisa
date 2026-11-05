#!/usr/bin/env python3
"""
Vizin — Preparação dos prompts para entrevistas isoladas (modo Claude em sessões separadas)

Versão: v1.1 (2026-11-04)
Histórico de mudanças:
  v1.1 (2026-11-04) Criação. Gera um arquivo de prompt por persona e rodada em simulacao_claude/prompts/.
                    Cada sessão de entrevista lê SÓ o seu arquivo, sem ver as outras personas (isolamento).

Uso: python3 simulacao/preparar_prompts.py [--rodadas 3]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simular  # reaproveita o mesmo texto de instruções e a mesma montagem do questionário

RAIZ = simular.RAIZ
PASTA = RAIZ / "simulacao_claude"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rodadas", type=int, default=3)
    a = ap.parse_args()
    personas = simular.carregar_json("personas.json")
    q = {"lojista": simular.carregar_json("questionario_lojista.json"),
         "consumidor": simular.carregar_json("questionario_consumidor.json")}
    (PASTA / "prompts").mkdir(parents=True, exist_ok=True)
    (PASTA / "respostas").mkdir(parents=True, exist_ok=True)
    n = 0
    for p in personas["lojistas"] + personas["consumidores"]:
        for r in range(1, a.rodadas + 1):
            texto = simular.SISTEMA + "\n\n" + simular.montar_usuario(p, q[p["tipo"]])
            (PASTA / "prompts" / f'{p["id"]}_r{r}.txt').write_text(texto, encoding="utf-8")
            n += 1
    print(f"{n} prompts gerados em {PASTA / 'prompts'}")


if __name__ == "__main__":
    main()
