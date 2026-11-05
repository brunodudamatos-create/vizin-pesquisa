#!/usr/bin/env python3
"""
Vizin — Análise dos resultados da simulação

Versão: v1.1 (2026-11-04)
Histórico de mudanças:
  v1.0 (2026-11-04) Criação. Lê respostas_brutas.jsonl e gera CSV, resumo.json (para o site) e Excel com gráficos.
                    Bloqueia dados de teste (MOCK) por padrão e emite alertas anti-viés.
  v1.1 (2026-11-04) Separa os resultados por modelo/origem (--origem). Cada origem grava em resultados/<origem>/.
                    Dados de teste (MOCK) só bloqueiam a análise da própria origem MOCK.

Uso:
  python3 simulacao/analisar.py --origem claude-isolado   # análise das entrevistas feitas pelo Claude
  python3 simulacao/analisar.py --origem gemini           # análise das entrevistas feitas pelo Gemini
  python3 simulacao/analisar.py --origem MOCK --permitir-mock # só para TESTAR o programa

Precisa de: openpyxl (pip install openpyxl) — só para gerar o Excel.
"""
import argparse, csv, json, sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
RES = RAIZ / "resultados"
LIMITE_VIES = 0.80  # acima disso, a simulação provavelmente está "viciada" (concordando demais)


def carregar(nome):
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


def ler_respostas(permitir_mock, origem):
    arq = RES / "respostas_brutas.jsonl"
    if not arq.exists():
        sys.exit("Ainda não há respostas. Rode primeiro: python3 simulacao/simular.py")
    regs = [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]
    origens = sorted({r["origem"] for r in regs})
    if origem is None:
        if len(origens) != 1:
            sys.exit(f"Há mais de uma origem nos dados: {origens}. Escolha uma com --origem.")
        origem = origens[0]
    regs = [r for r in regs if r["origem"] == origem]
    if not regs:
        sys.exit(f"Nenhuma resposta com origem '{origem}'. Origens existentes: {origens}")
    mocks = [r for r in regs if r["origem"] == "MOCK"]
    if mocks and not permitir_mock:
        sys.exit("ERRO: o arquivo contém respostas de TESTE (MOCK). Elas são aleatórias e NÃO podem virar resultado.\n"
                 "Apague resultados/respostas_brutas.jsonl e rode a simulação de verdade, ou use --permitir-mock só para testar.")
    return regs, bool(mocks), origem


def num(cod):
    return ord(cod) - ord("a") + 1


def distribuicao(regs, tipo, pergunta):
    c = Counter()
    n = 0
    for r in regs:
        if r["tipo"] != tipo:
            continue
        v = r["respostas"][pergunta["id"]]["resposta"]
        n += 1
        for cod in (v if isinstance(v, list) else [v]):
            c[cod] += 1
    linhas = []
    for o in pergunta["opcoes"]:
        qtd = c.get(o["cod"], 0)
        linhas.append({"cod": o["cod"], "texto": o["texto"], "qtd": qtd, "pct": round(100 * qtd / n, 1) if n else 0})
    return {"id": pergunta["id"], "texto": pergunta["texto"], "tipo": pergunta["tipo"], "n_respostas": n, "opcoes": linhas}


def consistencia(regs, tipo, quest):
    """Em quantas perguntas todas as rodadas da mesma persona deram a mesma resposta (estabilidade)."""
    por = defaultdict(lambda: defaultdict(list))
    for r in regs:
        if r["tipo"] == tipo:
            for pid, v in r["respostas"].items():
                por[r["persona_id"]][pid].append(json.dumps(v["resposta"]))
    out = {}
    for persona, d in por.items():
        iguais = sum(1 for vals in d.values() if len(set(vals)) == 1)
        out[persona] = round(100 * iguais / len(d), 1)
    return out


def gerar_resumo(regs, lojista, consumidor, tem_mock):
    resumo = {"_versao": "v1.0", "teste_mock": tem_mock,
              "aviso": "Dados SINTÉTICOS gerados por IA a partir de personas fictícias. Servem para explorar hipóteses e mapear atritos; não medem a demanda real do mercado.",
              "total_respostas": len(regs), "lojista": {}, "consumidor": {}, "alertas": [], "por_persona": {}}
    for tipo, quest in (("lojista", lojista), ("consumidor", consumidor)):
        resumo[tipo] = {"titulo": quest["titulo"],
                        "n_respostas": sum(1 for r in regs if r["tipo"] == tipo),
                        "n_personas": len({r["persona_id"] for r in regs if r["tipo"] == tipo}),
                        "perguntas": [distribuicao(regs, tipo, p) for p in quest["perguntas"]],
                        "consistencia_por_persona_pct": consistencia(regs, tipo, quest)}

    # --- indicadores e alertas anti-viés
    loj = [r for r in regs if r["tipo"] == "lojista"]
    if loj:
        adere = sum(1 for r in loj if r["respostas"]["Q4"]["resposta"] in ("d", "e")) / len(loj)
        resumo["lojista"]["indicador_disposicao_pct"] = round(100 * adere, 1)
        if adere > LIMITE_VIES:
            resumo["alertas"].append(f"Lojistas: {adere:.0%} responderam 'Disposto' ou 'Totalmente disposto' (Q4). Acima de {LIMITE_VIES:.0%} indica viés de concordância; revise as personas.")
        if all(r["respostas"]["Q4"]["resposta"] in ("d", "e") for r in loj):
            resumo["alertas"].append("Lojistas: NENHUMA recusa na Q4. Uma simulação realista precisa de recusas.")
        pagar = sum(1 for r in loj if r["respostas"]["Q6"]["resposta"] != "a") / len(loj)
        resumo["lojista"]["indicador_aceita_pagar_pct"] = round(100 * pagar, 1)
    con = [r for r in regs if r["tipo"] == "consumidor"]
    if con:
        m12 = sum(num(r["respostas"]["Q12"]["resposta"]) for r in con) / len(con)
        m13 = sum(num(r["respostas"]["Q13"]["resposta"]) for r in con) / len(con)
        resumo["consumidor"]["media_q12_atrapalha"] = round(m12, 2)
        resumo["consumidor"]["media_q13_desiste"] = round(m13, 2)
        alta = sum(1 for r in con if r["respostas"]["Q12"]["resposta"] in ("d", "e")) / len(con)
        if alta > LIMITE_VIES:
            resumo["alertas"].append(f"Consumidores: {alta:.0%} dizem que a dificuldade 'atrapalha muito' (Q12). Possível viés de concordância com o problema.")
    resumo["alertas"].append("Q4 e Q6 do lojista (disposição e quanto pagar) são hipotéticas e as mais sujeitas a otimismo; trate com menor confiança.")

    # --- por persona (média de rodadas)
    agrupado = defaultdict(list)
    for r in regs:
        agrupado[r["persona_id"]].append(r)
    for pid, rs in agrupado.items():
        item = {"nome_ficticio": rs[0]["nome_ficticio"], "tipo": rs[0]["tipo"], "rodadas": len(rs)}
        if rs[0]["tipo"] == "lojista":
            item["Q4_media"] = round(sum(num(x["respostas"]["Q4"]["resposta"]) for x in rs) / len(rs), 2)
            item["Q6_mais_comum"] = Counter(x["respostas"]["Q6"]["resposta"] for x in rs).most_common(1)[0][0]
        else:
            item["Q12_media"] = round(sum(num(x["respostas"]["Q12"]["resposta"]) for x in rs) / len(rs), 2)
            item["Q13_media"] = round(sum(num(x["respostas"]["Q13"]["resposta"]) for x in rs) / len(rs), 2)
        resumo["por_persona"][pid] = item
    return resumo


def gerar_csv(regs, lojista, consumidor):
    ids = {"lojista": [p["id"] for p in lojista["perguntas"]], "consumidor": [p["id"] for p in consumidor["perguntas"]]}
    for tipo in ("lojista", "consumidor"):
        arq = RES / f"respostas_{tipo}.csv"
        with arq.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["persona_id", "nome_ficticio", "rodada", "origem"] + ids[tipo])
            for r in regs:
                if r["tipo"] == tipo:
                    linha = []
                    for pid in ids[tipo]:
                        v = r["respostas"][pid]["resposta"]
                        linha.append("|".join(v) if isinstance(v, list) else v)
                    w.writerow([r["persona_id"], r["nome_ficticio"], r["rodada"], r["origem"]] + linha)


def gerar_excel(resumo, regs, lojista, consumidor):
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, Reference
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    wb.remove(wb.active)
    azul = PatternFill("solid", fgColor="1F4E79")
    branco = Font(bold=True, color="FFFFFF")

    ws = wb.create_sheet("Leia primeiro")
    linhas = ["Vizin — Pesquisa sintética (Tangará da Serra)", f"Versão {resumo['_versao']}", "",
              resumo["aviso"], ""]
    if resumo["teste_mock"]:
        linhas.insert(2, "⚠ DADOS DE TESTE (ALEATÓRIOS) — NÃO USAR COMO RESULTADO")
    linhas += ["Alertas anti-viés:"] + [f"- {a}" for a in resumo["alertas"]]
    for i, t in enumerate(linhas, 1):
        ws.cell(i, 1, t).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 120
    ws["A1"].font = Font(bold=True, size=14)

    for tipo, quest in (("lojista", lojista), ("consumidor", consumidor)):
        ws = wb.create_sheet(f"Resumo {tipo}")
        ws.cell(1, 1, f'{quest["titulo"]} — {resumo[tipo]["n_respostas"]} respostas de {resumo[tipo]["n_personas"]} personas').font = Font(bold=True, size=12)
        linha = 3
        for p in resumo[tipo]["perguntas"]:
            ws.cell(linha, 1, f'{p["id"]}. {p["texto"]}').font = Font(bold=True)
            linha += 1
            for j, h in enumerate(["Alternativa", "Quantidade", "%"], 1):
                c = ws.cell(linha, j, h); c.fill = azul; c.font = branco
            ini = linha + 1
            for o in p["opcoes"]:
                linha += 1
                ws.cell(linha, 1, f'{o["cod"]}) {o["texto"]}')
                ws.cell(linha, 2, o["qtd"]); ws.cell(linha, 3, o["pct"])
            fim = linha
            ch = BarChart(); ch.type = "bar"; ch.title = f'{p["id"]}'; ch.legend = None
            ch.height = 6; ch.width = 14
            ch.add_data(Reference(ws, min_col=3, min_row=ini - 1, max_row=fim), titles_from_data=True)
            ch.set_categories(Reference(ws, min_col=1, min_row=ini, max_row=fim))
            ws.add_chart(ch, f"E{ini - 1}")
            linha += 8
        ws.column_dimensions["A"].width = 75
        ws.column_dimensions["B"].width = 12

    ws = wb.create_sheet("Por persona")
    cab = ["ID", "Nome fictício", "Tipo", "Rodadas", "Indicador 1", "Indicador 2"]
    for j, h in enumerate(cab, 1):
        c = ws.cell(1, j, h); c.fill = azul; c.font = branco
    for i, (pid, d) in enumerate(sorted(resumo["por_persona"].items()), 2):
        ind1 = d.get("Q4_media", d.get("Q12_media")); ind2 = d.get("Q6_mais_comum", d.get("Q13_media"))
        for j, v in enumerate([pid, d["nome_ficticio"], d["tipo"], d["rodadas"], ind1, ind2], 1):
            ws.cell(i, j, v)
    n = len(resumo["por_persona"]) + 3
    ws.cell(n, 1, "Lojista: Indicador 1 = média da Q4 (1 a 5), Indicador 2 = faixa de pagamento mais frequente na Q6 (letra).")
    ws.cell(n + 1, 1, "Consumidor: Indicador 1 = média da Q12 (1 a 5), Indicador 2 = média da Q13 (1 a 5).")
    for col, w in zip("ABCDEF", (8, 18, 12, 10, 14, 14)):
        ws.column_dimensions[col].width = w

    ws = wb.create_sheet("Respostas brutas")
    cab = ["persona_id", "tipo", "rodada", "pergunta", "resposta", "porque"]
    for j, h in enumerate(cab, 1):
        c = ws.cell(1, j, h); c.fill = azul; c.font = branco
    i = 2
    for r in regs:
        for pid, v in r["respostas"].items():
            resp = "|".join(v["resposta"]) if isinstance(v["resposta"], list) else v["resposta"]
            for j, x in enumerate([r["persona_id"], r["tipo"], r["rodada"], pid, resp, v["porque"]], 1):
                ws.cell(i, j, x)
            i += 1
    ws.column_dimensions["F"].width = 90
    ws.freeze_panes = "A2"
    wb.save(RES / "vizin_simulacao.xlsx")


def main():
    global RES
    ap = argparse.ArgumentParser()
    ap.add_argument("--origem", help="qual conjunto analisar: claude-isolado, gemini, anthropic, MOCK")
    ap.add_argument("--permitir-mock", action="store_true", help="só para testar o programa")
    a = ap.parse_args()
    regs, tem_mock, origem = ler_respostas(a.permitir_mock, a.origem)
    RES = RES / origem          # cada origem grava na própria pasta
    RES.mkdir(parents=True, exist_ok=True)
    lojista, consumidor = carregar("questionario_lojista.json"), carregar("questionario_consumidor.json")
    resumo = gerar_resumo(regs, lojista, consumidor, tem_mock)
    resumo["origem"] = origem
    (RES / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    gerar_csv(regs, lojista, consumidor)
    gerar_excel(resumo, regs, lojista, consumidor)
    print("Gerados em resultados/<origem>/: resumo.json, respostas_lojista.csv, respostas_consumidor.csv, vizin_simulacao.xlsx")
    for al in resumo["alertas"]:
        print("ALERTA:", al)
    if tem_mock:
        print("\n*** ATENÇÃO: saída baseada em dados de TESTE (MOCK). Não use como resultado. ***")


if __name__ == "__main__":
    main()
