#!/usr/bin/env python3
"""
Vizin — Simulador de pesquisa sintética (entrevista individual por persona)

Versão: v1.0 (2026-11-04)
Histórico de mudanças:
  v1.0 (2026-11-04) Criação. Uma persona por vez, N rodadas, validação das respostas,
                    retomada automática, provedores Anthropic e Gemini, modo --mock para teste.

Como funciona (resumo):
  * Cada persona recebe o questionário real do grupo e responde SOZINHA (sem ver as outras).
  * A resposta precisa ser um JSON com códigos válidos (a, b, c...). Resposta inválida é refeita.
  * Cada resposta vem com uma justificativa curta ("porque"), usada no storytelling do pitch.
  * Tudo é gravado em resultados/respostas_brutas.jsonl; se o programa parar, basta rodar de novo.
  * Só usa a biblioteca padrão do Python (sem pip install).

ATENÇÃO: os dados gerados são SINTÉTICOS. Servem para explorar hipóteses e mapear atritos,
não para medir a demanda real do mercado.
"""
import argparse, json, os, random, sys, time, urllib.request, urllib.error
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDA = RAIZ / "resultados" / "respostas_brutas.jsonl"


def carregar_env():
    """Lê o arquivo .env (se existir) sem precisar de biblioteca externa."""
    env = RAIZ / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def carregar_json(nome):
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- prompts
SISTEMA = """Você vai responder a uma pesquisa de opinião como a pessoa descrita na ficha, e SOMENTE como ela.

Regras:
1. Responda com o conhecimento, o vocabulário, os receios e as limitações dessa pessoa. Não seja educado por padrão e não concorde por cortesia.
2. Escolha a alternativa que essa pessoa realmente marcaria. Alternativas negativas ("Nada disposto", "Não estaria disposto a pagar", "Não vejo necessidade") são tão válidas quanto as positivas quando o perfil indicar isso.
3. As respostas precisam ser coerentes entre si (quem diz que não sabe usar tecnologia não responde como quem vive no Instagram).
4. Para cada pergunta, escreva em "porque" UMA frase curta, na voz da pessoa, explicando a escolha.
5. Responda SOMENTE com JSON válido, sem texto antes ou depois, no formato:
{"Q1": {"resposta": "a", "porque": "..."}, "Q2": {"resposta": "c", "porque": "..."}}
   - Pergunta de escolha única: "resposta" é UMA letra.
   - Pergunta de múltipla escolha: "resposta" é uma LISTA de letras, por exemplo ["a", "f"].
   - Quando uma alternativa pedir complemento (por exemplo "Qual?" ou "Outro"), acrescente o campo "texto_livre" nessa pergunta.
"""


def montar_pergunta(p):
    linhas = [f'{p["id"]}. {p["texto"]}']
    if p["tipo"] == "multipla":
        linhas.append("(múltipla escolha: responda com uma lista de letras)")
    for o in p["opcoes"]:
        linhas.append(f'   {o["cod"]}) {o["texto"]}')
    return "\n".join(linhas)


def montar_usuario(persona, questionario):
    ficha = {k: v for k, v in persona.items() if k not in ("fonte_da_premissa",)}
    texto = "FICHA DA PESSOA:\n" + json.dumps(ficha, ensure_ascii=False, indent=2)
    texto += f'\n\nPESQUISA: {questionario["titulo"]}\n\n'
    texto += "\n\n".join(montar_pergunta(p) for p in questionario["perguntas"])
    texto += "\n\nResponda agora, em JSON, como essa pessoa."
    return texto


# ---------------------------------------------------------------- provedores
def _post(url, headers, corpo, tentativas=4):
    dados = json.dumps(corpo).encode("utf-8")
    for t in range(tentativas):
        req = urllib.request.Request(url, data=dados, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 529) and t < tentativas - 1:
                espera = 5 * (t + 1)
                print(f"   [aviso] HTTP {e.code}, tentando de novo em {espera}s…", flush=True)
                time.sleep(espera)
                continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError) as e:
            if t < tentativas - 1:
                time.sleep(5 * (t + 1))
                continue
            raise RuntimeError(f"Falha de rede: {e}")


def chamar_anthropic(sistema, usuario, temperatura):
    chave = os.environ.get("ANTHROPIC_API_KEY")
    if not chave:
        sys.exit("Falta ANTHROPIC_API_KEY no arquivo .env")
    modelo = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    r = _post("https://api.anthropic.com/v1/messages",
              {"x-api-key": chave, "anthropic-version": "2023-06-01", "content-type": "application/json"},
              {"model": modelo, "max_tokens": 3000, "temperature": temperatura, "system": sistema,
               "messages": [{"role": "user", "content": usuario}]})
    return "".join(b.get("text", "") for b in r["content"]), modelo


def chamar_gemini(sistema, usuario, temperatura):
    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        sys.exit("Falta GEMINI_API_KEY no arquivo .env")
    modelo = os.environ.get("GEMINI_MODEL")
    if not modelo:
        sys.exit("Falta GEMINI_MODEL no arquivo .env (copie o nome do modelo gratuito vigente no Google AI Studio)")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}"
    r = _post(url, {"content-type": "application/json"},
              {"systemInstruction": {"parts": [{"text": sistema}]},
               "contents": [{"role": "user", "parts": [{"text": usuario}]}],
               "generationConfig": {"temperature": temperatura, "responseMimeType": "application/json"}})
    return r["candidates"][0]["content"]["parts"][0]["text"], modelo


def chamar_mock(persona, questionario, semente):
    """Respostas ALEATÓRIAS só para testar o programa. Nunca use como resultado."""
    rng = random.Random(semente)
    out = {}
    for p in questionario["perguntas"]:
        cods = [o["cod"] for o in p["opcoes"]]
        if p["tipo"] == "multipla":
            resp = sorted(rng.sample(cods, rng.randint(1, 3)))
        else:
            resp = rng.choice(cods)
        out[p["id"]] = {"resposta": resp, "porque": "[MOCK] resposta aleatória de teste"}
    return json.dumps(out, ensure_ascii=False), "MOCK"


# ---------------------------------------------------------------- validação
def extrair_json(texto):
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
    i, f = texto.find("{"), texto.rfind("}")
    if i < 0 or f < 0:
        raise ValueError("sem JSON na resposta")
    return json.loads(texto[i:f + 1])


def validar(resp, questionario):
    """Confere se todas as perguntas foram respondidas com códigos existentes."""
    limpo = {}
    for p in questionario["perguntas"]:
        if p["id"] not in resp:
            raise ValueError(f'falta {p["id"]}')
        item = resp[p["id"]]
        cods = {o["cod"] for o in p["opcoes"]}
        r = item.get("resposta")
        if p["tipo"] == "multipla":
            if isinstance(r, str):
                r = [r]
            if not r or not all(x in cods for x in r):
                raise ValueError(f'{p["id"]}: códigos inválidos {r}')
            r = sorted(set(r))
        else:
            if isinstance(r, list) and len(r) == 1:
                r = r[0]
            if r not in cods:
                raise ValueError(f'{p["id"]}: código inválido {r}')
        limpo[p["id"]] = {"resposta": r, "porque": str(item.get("porque", ""))[:400],
                          "texto_livre": str(item.get("texto_livre", ""))[:200]}
    return limpo


# ---------------------------------------------------------------- principal
def ja_feitos():
    feitos = set()
    if SAIDA.exists():
        for linha in SAIDA.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                d = json.loads(linha)
                feitos.add((d["persona_id"], d["rodada"], d["origem"]))
    return feitos


def main():
    ap = argparse.ArgumentParser(description="Simulador de pesquisa sintética do Vizin")
    ap.add_argument("--provedor", choices=["anthropic", "gemini"], default="anthropic")
    ap.add_argument("--rodadas", type=int, default=3, help="quantas vezes cada persona responde (padrão 3)")
    ap.add_argument("--temperatura", type=float, default=1.0)
    ap.add_argument("--so", help="rodar só uma persona, ex.: --so L02")
    ap.add_argument("--mock", action="store_true", help="MODO TESTE: respostas aleatórias, sem chamar IA")
    a = ap.parse_args()

    carregar_env()
    personas = carregar_json("personas.json")
    q = {"lojista": carregar_json("questionario_lojista.json"),
         "consumidor": carregar_json("questionario_consumidor.json")}
    todas = personas["lojistas"] + personas["consumidores"]
    if a.so:
        todas = [p for p in todas if p["id"] == a.so]
        if not todas:
            sys.exit(f"Persona {a.so} não existe")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    feitos = ja_feitos()
    origem = "MOCK" if a.mock else a.provedor
    total = len(todas) * a.rodadas
    n = 0
    for persona in todas:
        quest = q[persona["tipo"]]
        for rodada in range(1, a.rodadas + 1):
            n += 1
            if (persona["id"], rodada, origem) in feitos:
                print(f"[{n}/{total}] {persona['id']} rodada {rodada}: já feita, pulando")
                continue
            print(f"[{n}/{total}] {persona['id']} {persona['nome_ficticio']} rodada {rodada}…", flush=True)
            ultimo_erro = None
            for tentativa in range(3):
                try:
                    if a.mock:
                        bruto, modelo = chamar_mock(persona, quest, f"{persona['id']}-{rodada}-{tentativa}")
                    else:
                        fn = chamar_anthropic if a.provedor == "anthropic" else chamar_gemini
                        bruto, modelo = fn(SISTEMA, montar_usuario(persona, quest), a.temperatura)
                    respostas = validar(extrair_json(bruto), quest)
                    break
                except (ValueError, KeyError, json.JSONDecodeError) as e:
                    ultimo_erro = e
                    print(f"   [aviso] resposta inválida ({e}); refazendo", flush=True)
            else:
                print(f"   [ERRO] {persona['id']} rodada {rodada} descartada: {ultimo_erro}")
                continue
            registro = {"persona_id": persona["id"], "tipo": persona["tipo"], "nome_ficticio": persona["nome_ficticio"],
                        "rodada": rodada, "origem": origem, "modelo": modelo,
                        "temperatura": a.temperatura, "data": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "respostas": respostas}
            with SAIDA.open("a", encoding="utf-8") as f:   # grava a cada resposta: seguro contra quedas
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            if not a.mock:
                time.sleep(1)
    print(f"\nPronto. Resultados em {SAIDA}")
    print("Próximo passo: python3 simulacao/analisar.py")


if __name__ == "__main__":
    main()
