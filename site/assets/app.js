/* Vizin — funções comuns do site | Versão v2.0 (2026-11-05)
   Histórico: v1.2 criação. v1.3 página Cenário multiagente, créditos da equipe no rodapé. v1.4 página Claude × Gemini. v1.5 versão do site. v1.6 brasão da UNEMAT, aviso institucional no rodapé e faixa de título nas páginas internas. v1.7 versão do site. v1.8 nova ordem do menu (segue a lógica do método). v1.9 versão do site. v2.0 página Diagnóstico local no menu e versão do site. */
"use strict";
const VERSAO = "v2.0";
const REPO = "https://github.com/brunodudamatos-create/vizin-pesquisa";
const PAGINAS = [
  ["index", "Início"], ["metodologia", "Metodologia"], ["personas", "Personas"], ["transcricoes", "Entrevistas"],
  ["cenario", "Cenário multiagente"], ["diagnostico", "Diagnóstico local"], ["resultados", "Resultados"], ["modelos", "Claude × Gemini"], ["comparar", "Sintético × Real"],
];

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function fmt(n) { return (Math.round(n * 10) / 10).toLocaleString("pt-BR") + "%"; }
function norm(s) {
  return String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}
async function pegaJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}
async function pegaTexto(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.text();
}
async function pegaJSONL(url) {
  return (await pegaTexto(url)).split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
}
async function manifest() {
  try { return await pegaJSON("data/manifest.json"); } catch (e) { return { origens: [] }; }
}
const NOME_ORIGEM = {
  "claude-isolado": "Claude (sessões isoladas)", gemini: "Gemini (servidor)", anthropic: "Claude via API",
  "claude-isolado-neutro": "Claude, ficha neutra (controle)", "gemini-neutro": "Gemini, ficha neutra (controle)",
};
function nomeOrigem(o) { return NOME_ORIGEM[o] || o; }

function montarTopo(atual) {
  const menu = PAGINAS.map(([id, nome]) =>
    `<a href="${id}.html"${id === atual ? ' aria-current="page"' : ""}>${esc(nome)}</a>`).join("");
  document.getElementById("topo").innerHTML =
    `<header class="topo"><div class="wrap"><a class="marca" href="index.html">Vizin<span>·</span>pesquisa</a><nav class="menu" aria-label="Principal">${menu}</nav></div></header>`;
  document.getElementById("rodape").innerHTML =
    `<footer class="rodape"><div class="wrap"><p>Dados <strong>sintéticos</strong> gerados por IA a partir de personas fictícias, para explorar hipóteses e mapear atritos de adoção. Não medem a demanda real do mercado.</p>` +
    `<div class="rodape-inst"><img src="assets/brasao-unemat.png" alt="Brasão da UNEMAT" height="64"><div>` +
    `<p>Equipe: Bruno Duda Dantas Matos, Kamilly Vitória Oliveira Araujo, Lukas Ramos Rezende e Victor Hugo Borsato Xavier (simulação multiagente).</p>` +
    `<p>Projeto desenvolvido no âmbito da pós-graduação em Gestão e Inovação da UNEMAT. Trabalho acadêmico de estudantes, e não um site oficial da universidade.</p>` +
    `<p>Site ${VERSAO} · <a href="${REPO}">Código e dados no GitHub</a></p></div></div></div></footer>`;
}

/* Barras horizontais. linhas = [{rot, s, r}] em porcentagem (0-100). */
function barras(el, linhas, temReal) {
  el.innerHTML = linhas.map((l) =>
    `<div class="barra-linha${temReal ? " duplo" : ""}"><div class="rot">${esc(l.rot)}</div>` +
    `<div class="trilho${temReal ? " duplo" : ""}"><i class="s" style="width:${Math.max(0, Math.min(100, l.s))}%"></i>` +
    `${temReal ? `<i class="r" style="width:${Math.max(0, Math.min(100, l.r))}%"></i>` : ""}</div>` +
    `<div class="pct">${fmt(l.s)}${temReal ? ` · ${fmt(l.r)}` : ""}</div></div>`).join("");
}

function opcaoTexto(pergunta, cod) {
  const o = pergunta.opcoes.find((x) => x.cod === cod);
  return o ? o.texto : cod;
}

/* Faixa de título das páginas internas (a Início já tem a sua). Move o h1 e o .lead para uma faixa azul-marinho. */
function montarFaixa(atual) {
  if (atual === "index") return;
  const h1 = document.querySelector("main h1"); if (!h1) return;
  const lead = document.querySelector("main .lead");
  const wrapOrig = h1.closest(".wrap");
  const nome = (PAGINAS.find((p) => p[0] === atual) || [, ""])[1];
  const faixa = document.createElement("section");
  faixa.className = "hero hero-menor";
  const wrap = document.createElement("div");
  wrap.className = "wrap";
  if (wrapOrig && wrapOrig.style.maxWidth) wrap.style.maxWidth = wrapOrig.style.maxWidth;
  const eb = document.createElement("p");
  eb.className = "eyebrow"; eb.textContent = `Vizin · plataforma de validação prévia · ${nome}`;
  wrap.appendChild(eb); wrap.appendChild(h1); if (lead) wrap.appendChild(lead);
  faixa.appendChild(wrap);
  document.querySelector("main").before(faixa);
}

document.addEventListener("DOMContentLoaded", () => {
  const atual = document.body.dataset.pagina || "";
  montarTopo(atual);
  montarFaixa(atual);
});
