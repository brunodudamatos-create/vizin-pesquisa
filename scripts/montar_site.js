#!/usr/bin/env node
/*
 * Vizin — Montagem dos dados do site
 * Versão: v1.2 (2026-11-04)
 * Histórico de mudanças:
 *   v1.2 (2026-11-04) Criação. Copia dados/, resultados/ e simulacao_claude/ para site/data/ e gera manifest.json.
 *                     Dados de TESTE (origem MOCK) nunca entram no site.
 * Roda sozinho no Vercel (buildCommand) e também no computador: node scripts/montar_site.js
 */
const fs = require("fs");
const path = require("path");

const RAIZ = path.resolve(__dirname, "..");
const DESTINO = path.join(RAIZ, "site", "data");

fs.rmSync(DESTINO, { recursive: true, force: true });
fs.mkdirSync(DESTINO, { recursive: true });

function copiar(origem, destino, filtro) {
  if (!fs.existsSync(origem)) return;
  fs.cpSync(origem, destino, { recursive: true, filter: filtro || (() => true) });
}

// Dados de entrada (personas e questionários)
copiar(path.join(RAIZ, "dados"), path.join(DESTINO, "dados"));

// Resultados: só pastas de origem com resumo.json, e nunca MOCK
const origens = [];
const resDir = path.join(RAIZ, "resultados");
if (fs.existsSync(resDir)) {
  for (const nome of fs.readdirSync(resDir)) {
    const p = path.join(resDir, nome);
    if (fs.statSync(p).isDirectory() && nome !== "MOCK" && fs.existsSync(path.join(p, "resumo.json"))) {
      origens.push(nome);
      copiar(p, path.join(DESTINO, "resultados", nome), (src) => !src.endsWith(".xlsx") || true);
    }
  }
  const brutas = path.join(resDir, "respostas_brutas.jsonl");
  if (fs.existsSync(brutas)) {
    const linhas = fs.readFileSync(brutas, "utf8").split("\n").filter((l) => l.trim());
    const ok = linhas.filter((l) => {
      try { return JSON.parse(l).origem !== "MOCK"; } catch (e) { return false; }
    });
    fs.mkdirSync(path.join(DESTINO, "resultados"), { recursive: true });
    fs.writeFileSync(path.join(DESTINO, "resultados", "respostas_brutas.jsonl"), ok.join("\n") + "\n");
  }
}

// Prompts e respostas brutas das entrevistas isoladas
copiar(path.join(RAIZ, "simulacao_claude"), path.join(DESTINO, "simulacao_claude"));

fs.writeFileSync(
  path.join(DESTINO, "manifest.json"),
  JSON.stringify({ versao: "v1.4", gerado_em: new Date().toISOString(), origens: origens.sort() }, null, 2)
);
console.log(`Site montado. Origens publicadas: ${origens.join(", ") || "(nenhuma)"}`);
