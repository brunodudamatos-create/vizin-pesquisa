#!/usr/bin/env python3
"""
Vizin — Importa as respostas das entrevistas isoladas (Claude) para o arquivo de resultados

Versão: v1.2 (2026-11-05)
Histórico de mudanças:
  v1.2 (2026-11-05) Opção --ficha neutra: importa simulacao_claude_neutro/respostas com origem "claude-isolado-neutro".
  v1.1 (2026-11-04) Criação. Lê simulacao_claude/respostas/*.json, valida com as mesmas regras do simulador
                    e grava em resultados/respostas_brutas.jsonl com origem "claude-isolado".

Uso: python3 simulacao/importar_transcricoes.py [--ficha neutra]
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simular

MODELO = "Claude (subagente isolado, sessão limpa por persona e rodada)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ficha", choices=["completa", "neutra"], default="completa")
    ap.add_argument("--modelo", default=MODELO, help="texto que descreve o modelo, gravado em cada registro")
    a = ap.parse_args()
    ORIGEM = "claude-isolado" + ("-neutro" if a.ficha == "neutra" else "")
    personas = simular.carregar_json("personas.json")
    todas = {p["id"]: p for p in personas["lojistas"] + personas["consumidores"]}
    q = {"lojista": simular.carregar_json("questionario_lojista.json"),
         "consumidor": simular.carregar_json("questionario_consumidor.json")}
    feitos = simular.ja_feitos()
    pasta = simular.RAIZ / ("simulacao_claude_neutro" if a.ficha == "neutra" else "simulacao_claude") / "respostas"
    ok = erro = pulados = 0
    for arq in sorted(pasta.glob("*.json")):
        pid, r = arq.stem.split("_r")
        r = int(r)
        if (pid, r, ORIGEM) in feitos:
            pulados += 1
            continue
        try:
            resp = simular.validar(simular.extrair_json(arq.read_text(encoding="utf-8")), q[todas[pid]["tipo"]])
        except Exception as e:
            print(f"[ERRO] {arq.name}: {e}")
            erro += 1
            continue
        reg = {"persona_id": pid, "tipo": todas[pid]["tipo"], "nome_ficticio": todas[pid]["nome_ficticio"],
               "rodada": r, "origem": ORIGEM, "modelo": a.modelo, "temperatura": None,
               "data": time.strftime("%Y-%m-%d %H:%M:%S"), "respostas": resp}
        with simular.SAIDA.open("a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
        ok += 1
    print(f"Importadas: {ok} | já existentes: {pulados} | com erro: {erro}")


if __name__ == "__main__":
    main()
