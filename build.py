import json, urllib.request, urllib.parse, re, unicodedata, os, sys
from datetime import datetime, timezone
from collections import defaultdict

TOKEN = os.environ["DEMANDASRIO_TOKEN"]
BASE = "https://app.demandasrio.com.br/api/1.1/obj"
REPO_DIR = "."  # roda a partir da raiz do repo (checkout do GitHub Actions)


def get(path, params=""):
    url = f"{BASE}/{path}{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


constraints = [
    {"key": "Procedimento", "constraint_type": "equals", "value": "Microchipagem"},
    {"key": "Data", "constraint_type": "greater than", "value": "2026-05-19T23:59:59.000Z"},
]
enc = urllib.parse.quote(json.dumps(constraints))
all_rows = []
cursor = 0
while True:
    d = get("Castramovel", f"?constraints={enc}&limit=100&cursor={cursor}")
    resp = d["response"]
    all_rows.extend(resp["results"])
    if resp["remaining"] <= 0:
        break
    cursor += len(resp["results"])

unique_ids = sorted(set(r.get("Bairro") for r in all_rows if r.get("Bairro")))
bairro_lookup = {}
for bid in unique_ids:
    try:
        d = get(f"Bairros/{bid}")
        b = d["response"]
        bairro_lookup[bid] = {"nome": b["Bairro"], "regiao": b.get("Região", "")}
    except Exception as e:
        print("ERRO ao buscar bairro", bid, e, file=sys.stderr)

records = []
for row in all_rows:
    info = bairro_lookup.get(row.get("Bairro"))
    nome = info["nome"] if info else "(desconhecido)"
    records.append({
        "bairro": nome, "regiao": row.get("Região", ""), "data": row.get("Data"),
        "tutores": row.get("Qtd cadastros", 0) or 0, "animais": row.get("Qtd de animais", 0) or 0,
    })

by_bairro = defaultdict(lambda: {"acoes": 0, "animais": 0, "tutores": 0, "regiao": ""})
for r in records:
    b = by_bairro[r["bairro"]]
    b["acoes"] += 1; b["animais"] += r["animais"]; b["tutores"] += r["tutores"]; b["regiao"] = r["regiao"]
bairros_out = sorted([{"bairro": k, **v} for k, v in by_bairro.items()], key=lambda x: -x["animais"])

by_regiao = defaultdict(lambda: {"acoes": 0, "animais": 0, "tutores": 0, "bairros": set()})
for r in records:
    rg = by_regiao[r["regiao"]]
    rg["acoes"] += 1; rg["animais"] += r["animais"]; rg["tutores"] += r["tutores"]; rg["bairros"].add(r["bairro"])
regioes_out = sorted(
    [{"regiao": k, "acoes": v["acoes"], "animais": v["animais"], "tutores": v["tutores"], "bairros": len(v["bairros"])}
     for k, v in by_regiao.items()], key=lambda x: -x["animais"])

totais = {
    "acoes": sum(b["acoes"] for b in bairros_out), "animais": sum(b["animais"] for b in bairros_out),
    "tutores": sum(b["tutores"] for b in bairros_out), "bairros_atendidos": len(bairros_out),
    "regioes_atendidas": len(regioes_out),
}
AGG = {"bairros": bairros_out, "regioes": regioes_out, "totais": totais}
SERIES = sorted([{"data": r["data"], "animais": r["animais"]} for r in records], key=lambda x: x["data"])


def normalize(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).strip().lower()


master = json.load(open(os.path.join(REPO_DIR, "votacao_master.json"), encoding="utf-8"))
norm_index = {}
for m in master:
    key = normalize(m["bairro"])
    if key not in norm_index:
        norm_index[key] = m


def resolve(bairro, regiao):
    if normalize(bairro) == "freguesia":
        key = normalize("Freguesia (Ilha Do Governador)") if (regiao and "ilha" in normalize(regiao)) else normalize("Freguesia")
        return norm_index.get(key)
    return norm_index.get(normalize(bairro))


covered = []
covered_norm = set()
for b in bairros_out:
    m = resolve(b["bairro"], b["regiao"])
    if m:
        covered.append({"bairro": b["bairro"], "votos": m["votos"]})
        covered_norm.add(normalize(m["bairro"]))
    else:
        print("AVISO: bairro atendido sem correspondencia na votacao:", b["bairro"], file=sys.stderr)
pending = [m for m in master if normalize(m["bairro"]) not in covered_norm]
covered.sort(key=lambda x: -x["votos"]); pending.sort(key=lambda x: -x["votos"])
VOTACAO = {"covered": covered, "pending": pending}

if records:
    raw_dates = sorted(r["data"] for r in records)
    periodo_ini = datetime.fromisoformat(raw_dates[0].replace("Z", "+00:00")).strftime("%d/%m/%Y")
    periodo_fim = datetime.fromisoformat(raw_dates[-1].replace("Z", "+00:00")).strftime("%d/%m/%Y")
else:
    periodo_ini = periodo_fim = "N/A"
agora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

template = open(os.path.join(REPO_DIR, "template.html"), encoding="utf-8").read()

new_header = f'<p>Cidade do Rio de Janeiro · Período dos dados: {periodo_ini} a {periodo_fim} · Fonte: API do sistema (dados ao vivo, produção) · Atualizado em {agora}</p>'
template = re.sub(r'<p>Cidade do Rio de Janeiro.*?</p>', new_header, template, count=1, flags=re.DOTALL)

template = re.sub(r'const AGG = \{.*?\};\n', f'const AGG = {json.dumps(AGG, ensure_ascii=False)};\n', template, count=1, flags=re.DOTALL)
template = re.sub(r'const VOTACAO = \{.*?\};\n', f'const VOTACAO = {json.dumps(VOTACAO, ensure_ascii=False)};\n', template, count=1, flags=re.DOTALL)
# usa [.*?] em vez de [] fixo: depois da 1a execucao o SERIES ja nao fica vazio no template
template = re.sub(r'const SERIES = \[.*?\];\n', f'const SERIES = {json.dumps(SERIES, ensure_ascii=False)};\n', template, count=1, flags=re.DOTALL)

template = re.sub(
    r'<p class="note" style="margin-bottom:14px;">.*?</p>',
    f'<p class="note" style="margin-bottom:14px;">Prioridade dos bairros pendentes segue a votação de Marcio Ribeiro (162 bairros votados). Os {len(covered)} bairros já atendidos foram cruzados com essa mesma lista.</p>',
    template, count=1, flags=re.DOTALL)

template = re.sub(r'<h3>✅ Bairros já atendidos \(\d+\) — por votos</h3>', f'<h3>✅ Bairros já atendidos ({len(covered)}) — por votos</h3>', template, count=1)
template = re.sub(r'<h3>⏳ Bairros pendentes \(\d+\) — por votos</h3>', f'<h3>⏳ Bairros pendentes ({len(pending)}) — por votos</h3>', template, count=1)

new_footer = f'<footer>Dados de execução das ações: API do sistema (demandasrio.com.br, produção), {totais["acoes"]} registros de Microchipagem entre {periodo_ini} e {periodo_fim}. Ranking de prioridade: planilha "MARCIO RIBEIRO 2024" (aba de votação por bairro, 162 bairros votados). Atualizado automaticamente.</footer>'
template = re.sub(r'<footer>.*?</footer>', new_footer, template, count=1, flags=re.DOTALL)

open(os.path.join(REPO_DIR, "index.html"), "w", encoding="utf-8").write(template)
print(json.dumps(totais, ensure_ascii=False))
print(f"Periodo: {periodo_ini} - {periodo_fim} | Atualizado: {agora}")
print(f"Covered: {len(covered)} Pending: {len(pending)} | SERIES: {len(SERIES)} registros")
