#!/usr/bin/env python3
"""
Vizin — Coleta de dados do IBGE para Tangará da Serra (MT)

Versão: v1.0 (2026-11-05)
Histórico de mudanças:
  v1.0 (2026-11-05) Criação. Baixa do IBGE (API SIDRA e API de Agregados) a população do Censo 2022 por idade
                    e as unidades locais de comércio (CEMPRE) do município 5107958. Salva as respostas brutas em
                    dados/ibge/ e um resumo em dados/ibge/LEIAME.txt. Usa só a biblioteca padrão do Python.

Importante: este script NUNCA foi executado pelo autor, porque a rede do ambiente de desenvolvimento não alcança o
IBGE. Ele guarda a resposta bruta de cada consulta, inclusive os erros, para que o ajuste seja feito com a resposta real.

Uso (no servidor):
  python3 simulacao/coletar_ibge.py            # só baixa e salva
  python3 simulacao/coletar_ibge.py --enviar   # baixa, salva e envia ao GitHub (git add, commit e push de dados/ibge)
"""
import argparse, json, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "ibge"
MUN = "5107958"  # Tangará da Serra (MT)

CONSULTAS = [
    ("censo2022_metadados_9514", "https://servicodados.ibge.gov.br/api/v3/agregados/9514/metadados"),
    ("censo2022_populacao_total", f"https://apisidra.ibge.gov.br/values/t/9514/n6/{MUN}/v/93/p/2022"),
    ("censo2022_populacao_por_idade", f"https://apisidra.ibge.gov.br/values/t/9514/n6/{MUN}/v/93/p/2022/c287/all"),
    ("cempre_metadados_6450", "https://servicodados.ibge.gov.br/api/v3/agregados/6450/metadados"),
    ("cempre_unidades_locais", f"https://apisidra.ibge.gov.br/values/t/6450/n6/{MUN}/v/all/p/last/c12762/all"),
]


def baixar(url, tentativas=3):
    ultimo = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "vizin-pesquisa/1.0 (projeto academico UNEMAT)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:  # rede
            ultimo = str(e)
            time.sleep(3 * (i + 1))
    return 0, ultimo.encode() if ultimo else b""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enviar", action="store_true", help="envia dados/ibge ao GitHub depois de baixar")
    args = ap.parse_args()
    SAIDA.mkdir(parents=True, exist_ok=True)
    linhas = [f"Coleta do IBGE para Tangará da Serra (código {MUN}), em {time.strftime('%Y-%m-%d %H:%M')}", ""]
    for nome, url in CONSULTAS:
        status, corpo = baixar(url)
        ext = "json"
        try:
            dado = json.loads(corpo.decode("utf-8"))
            texto = json.dumps(dado, ensure_ascii=False, indent=1)
            n = len(dado) if isinstance(dado, list) else 1
        except Exception:
            texto, ext, n = corpo.decode("utf-8", "replace"), "txt", 0
        (SAIDA / f"{nome}.{ext}").write_text(texto, encoding="utf-8")
        marca = "OK" if status == 200 else "FALHOU"
        linhas.append(f"{marca} [{status}] {nome}: {len(corpo)} bytes, {n} registros")
        print(linhas[-1])
    (SAIDA / "LEIAME.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\nArquivos salvos em dados/ibge/. Se alguma linha acima disser FALHOU, copie o resultado inteiro e envie ao Claude.")
    if args.enviar:
        subprocess.run(["git", "add", "dados/ibge"], cwd=RAIZ, check=False)
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=RAIZ)
        if r.returncode == 0:
            print("Nada novo para enviar.")
        else:
            subprocess.run(["git", "commit", "-q", "-m", "Dados brutos do IBGE para Tangará da Serra (coleta automática)"], cwd=RAIZ, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=RAIZ, check=True)
            print("Enviado ao GitHub.")


if __name__ == "__main__":
    sys.exit(main())
