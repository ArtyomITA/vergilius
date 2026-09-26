# -*- coding: utf-8 -*-
# Ricalcolo indipendente del banco System One.
# Legge SOLO i .jsonl grezzi (mai i -riepilogo.json ne' il referto.md).
# Nessun modello caricato, nessun uso GPU: solo lettura file e aritmetica.

import json
import statistics
from pathlib import Path

CARTELLA = Path(r"D:\vergilius-lab\ricerche\opt-1080\misure\system-one")

FILE_RUNS = {
    "210349_principale": CARTELLA / "banco-20260926-210349.jsonl",
    "211912_slot_sporco": CARTELLA / "banco-20260926-211912.jsonl",
    "212125_replica_pulita": CARTELLA / "banco-20260926-212125.jsonl",
    "212256_chat_sporca": CARTELLA / "banco-20260926-212256.jsonl",
    "212535_chat_quieta": CARTELLA / "banco-20260926-212535.jsonl",
}


def leggi_risposte(percorso):
    """Legge le righe tipo 'risposta' da un jsonl grezzo."""
    righe = []
    with open(percorso, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            d = json.loads(linea)
            if d.get("tipo") == "risposta":
                righe.append(d)
    return righe


def filtra(righe, braccio, passata):
    return [r for r in righe if r.get("braccio") == braccio and r.get("passata") == passata]


def mediana(vals):
    return statistics.median(vals) if vals else float("nan")


def p90(vals):
    """Nearest-rank: idx = ceil(0.9*n)-1. Verificato contro referto.md sulle
    3 categorie (35/25/40 campioni): unico metodo che riproduce le sue cifre
    esatte (0.235/0.287/0.346), a differenza dell'interpolazione lineare stile
    numpy che su n piccoli scarta di 1-3 millesimi."""
    if not vals:
        return float("nan")
    s = sorted(vals)
    n = len(s)
    import math
    idx = math.ceil(0.9 * n) - 1
    idx = max(0, min(n - 1, idx))
    return s[idx]


def accuratezza(righe):
    if not righe:
        return float("nan")
    return sum(1 for r in righe if r.get("corretta")) / len(righe)


def per_categoria(righe):
    cats = sorted(set(r["categoria"] for r in righe))
    out = {}
    for c in cats:
        sub = [r for r in righe if r["categoria"] == c]
        lat = [r["lat_s"] for r in sub]
        conf_ge = [r for r in sub if r["confidenza"] >= 0.7]
        conf_lt = [r for r in sub if r["confidenza"] < 0.7]
        out[c] = {
            "n": len(sub),
            "acc": accuratezza(sub),
            "conf_media": statistics.mean(r["confidenza"] for r in sub),
            "conf_ge_0.7_n": len(conf_ge),
            "conf_ge_0.7_acc": accuratezza(conf_ge),
            "conf_lt_0.7_acc": accuratezza(conf_lt),
            "lat_mediana": mediana(lat),
            "lat_p90": p90(lat),
        }
    return out


def ece_10_bin(righe, nbin=10):
    """ECE standard a bin di larghezza fissa 1/nbin su [0,1]."""
    bins = [[] for _ in range(nbin)]
    for r in righe:
        c = r["confidenza"]
        idx = min(nbin - 1, int(c * nbin))
        bins[idx].append(r)
    n_tot = len(righe)
    ece = 0.0
    dettaglio = []
    for i, b in enumerate(bins):
        if not b:
            continue
        acc_b = accuratezza(b)
        conf_b = statistics.mean(r["confidenza"] for r in b)
        peso = len(b) / n_tot
        ece += peso * abs(acc_b - conf_b)
        dettaglio.append({
            "fascia": f"{i/nbin:.2f}-{(i+1)/nbin:.2f}",
            "n": len(b),
            "acc": acc_b,
            "conf_media": conf_b,
        })
    return ece, dettaglio


def nll_brier(righe):
    """NLL e Brier MULTICLASSE sulla lettera giusta (non binario scelta/corretta):
    NLL = media di -log(prob[giusta]); Brier = media di sum_k (prob[k]-y_k)^2
    su tutte le lettere valide k, y_k=1 solo per k=giusta.
    Verificato: e' questa la formula che riproduce 0,831 / 0,394 del referto,
    non la versione binaria sulla sola lettera scelta (che da' 0,384 / 0,125)."""
    import math
    n = len(righe)
    nll = 0.0
    brier = 0.0
    for r in righe:
        prob = r["prob"]
        giusta = r["giusta"]
        p_true = min(max(prob.get(giusta, 1e-12), 1e-12), 1 - 1e-12)
        nll += -math.log(p_true)
        s = 0.0
        for k, p in prob.items():
            y = 1.0 if k == giusta else 0.0
            s += (p - y) ** 2
        brier += s
    return nll / n, brier / n


def verifica_coerenza(righe):
    """Controlla che 'corretta' == (scelta == giusta) e che confidenza == prob[scelta]."""
    problemi = []
    for r in righe:
        atteso_corretta = (r.get("scelta") == r.get("giusta"))
        if atteso_corretta != r.get("corretta"):
            problemi.append(("corretta_mismatch", r["id"], r.get("passata")))
        prob = r.get("prob", {})
        scelta = r.get("scelta")
        if scelta in prob:
            diff = abs(prob[scelta] - r.get("confidenza", -1))
            if diff > 1e-9:
                problemi.append(("confidenza_mismatch", r["id"], diff))
    return problemi


def soglia_copertura_acc(righe, soglia):
    sub = [r for r in righe if r["confidenza"] >= soglia]
    return len(sub) / len(righe), accuratezza(sub), len(sub)


def stampa_tabella_principale(righe_prefisso):
    print("=" * 100)
    print("RUN PRINCIPALE 210349 - passata PREFISSO - accuratezza per categoria")
    print("=" * 100)
    pc = per_categoria(righe_prefisso)
    tot_lat = [r["lat_s"] for r in righe_prefisso]
    for c, v in pc.items():
        print(f"{c:15s} n={v['n']:3d} acc={v['acc']*100:5.1f}% conf_media={v['conf_media']:.3f} "
              f"conf>=0.7 n={v['conf_ge_0.7_n']:2d} acc={v['conf_ge_0.7_acc']*100:5.1f}% "
              f"conf<0.7 acc={v['conf_lt_0.7_acc']*100:5.1f}% "
              f"lat_mediana={v['lat_mediana']:.3f}s p90={v['lat_p90']:.3f}s")
    print(f"{'TUTTE':15s} n={len(righe_prefisso):3d} acc={accuratezza(righe_prefisso)*100:5.1f}% "
          f"conf_media={statistics.mean(r['confidenza'] for r in righe_prefisso):.3f} "
          f"lat_mediana={mediana(tot_lat):.3f}s p90={p90(tot_lat):.3f}s")

    cop, acc, n = soglia_copertura_acc(righe_prefisso, 0.7)
    sotto = [r for r in righe_prefisso if r["confidenza"] < 0.7]
    print(f"\nSoglia conf>=0.7 (tutte le categorie): copertura={cop*100:.1f}% n={n} acc={acc*100:.1f}%")
    print(f"Sotto 0.7 (tutte le categorie): n={len(sotto)} acc={accuratezza(sotto)*100:.1f}%")
    sopra = [r for r in righe_prefisso if r["confidenza"] >= 0.7]
    errori_sopra = [r for r in sopra if not r["corretta"]]
    print(f"Errori sopra 0.7: {len(errori_sopra)}")
    for r in errori_sopra:
        print(f"  {r['id']} ({r['categoria']}): giusta={r['giusta']} scelta={r['scelta']} conf={r['confidenza']:.3f}")

    ece, dettaglio = ece_10_bin(righe_prefisso, 10)
    nll, brier = nll_brier(righe_prefisso)
    print(f"\nECE (10 bin larghezza fissa) = {ece:.6f}")
    print(f"NLL media = {nll:.6f}   Brier medio = {brier:.6f}")
    print("Dettaglio fasce ECE:")
    for d in dettaglio:
        print(f"  {d['fascia']}  n={d['n']:3d}  acc={d['acc']*100:5.1f}%  conf_media={d['conf_media']:.3f}")

    problemi = verifica_coerenza(righe_prefisso)
    print(f"\nControllo coerenza interna (corretta/confidenza): {len(problemi)} problemi")
    for p in problemi[:10]:
        print("  ", p)


def stampa_tabella_latenze():
    print("\n" + "=" * 100)
    print("LATENZE per tutti i 5 file grezzi (freddo / prefisso / ripetuta)")
    print("=" * 100)
    for nome, path in FILE_RUNS.items():
        righe = leggi_risposte(path)
        riga_out = [nome]
        for passata in ("freddo", "prefisso", "ripetuta"):
            sub = filtra(righe, "system_one", passata)
            if not sub:
                riga_out.append(f"{passata}: n/d")
                continue
            lat = [r["lat_s"] for r in sub]
            riga_out.append(f"{passata}: n={len(sub)} med={mediana(lat):.3f}s p90={p90(lat):.3f}s")
        print(" | ".join(riga_out))


def confronto_ragiona(righe_tutte):
    print("\n" + "=" * 100)
    print("Braccio RAGIONA (run principale) - per confronto (niente confidenza qui)")
    print("=" * 100)
    rag = [r for r in righe_tutte if r.get("braccio") == "ragiona"]
    cats = sorted(set(r["categoria"] for r in rag))
    for c in cats:
        sub = [r for r in rag if r["categoria"] == c]
        lat = [r["lat_s"] for r in sub]
        print(f"{c:15s} n={len(sub):3d} acc={accuratezza(sub)*100:5.1f}% lat_mediana={mediana(lat):.3f}s p90={p90(lat):.3f}s")
    lat = [r["lat_s"] for r in rag]
    print(f"{'TUTTE':15s} n={len(rag):3d} acc={accuratezza(rag)*100:5.1f}% lat_mediana={mediana(lat):.3f}s p90={p90(lat):.3f}s")


if __name__ == "__main__":
    righe_principale = leggi_risposte(FILE_RUNS["210349_principale"])
    righe_prefisso = filtra(righe_principale, "system_one", "prefisso")
    stampa_tabella_principale(righe_prefisso)
    stampa_tabella_latenze()
    confronto_ragiona(righe_principale)
