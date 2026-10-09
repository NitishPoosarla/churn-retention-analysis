"""01-telco-churn — 06_chat.py — ask-the-data chatbot (terminal, offline-capable).

THE RULE, extended to chat: every numeric answer is computed live from
data/processed/telco_clean.csv. If GROQ_API_KEY is set, the LLM receives
ONLY verified numbers and narrates them — it never computes.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "outputs"


# ----------------------------- computations -------------------------------

def compute(df: pd.DataFrame, q: str) -> dict:
    """Compute every metric the question implies, live from the data."""
    q_l = q.lower()
    facts: dict = {}

    if any(w in q_l for w in ("segment", "contract")):
        g = df.groupby("Contract").agg(customers=("churn_flag", "size"),
                                       churners=("churn_flag", "sum"),
                                       churn_rate=("churn_flag", "mean"))
        facts["by_contract"] = {i: {"customers": int(r.customers),
                                    "churn_rate": round(float(r.churn_rate), 4)}
                                for i, r in g.iterrows()}

    if "payment" in q_l:
        g = df.groupby("PaymentMethod")["churn_flag"].agg(["size", "mean"])
        facts["by_payment"] = {i: round(float(r["mean"]), 4) for i, r in g.iterrows()}

    if any(w in q_l for w in ("internet", "fiber", "dsl", "service")):
        g = df.groupby("InternetService").agg(customers=("churn_flag", "size"),
                                              churn_rate=("churn_flag", "mean"),
                                              churners=("churn_flag", "sum"))
        facts["by_internet"] = {i: {"customers": int(r.customers),
                                    "churn_rate": round(float(r.churn_rate), 4), "churners": int(r.churners)} for i, r in g.iterrows()}

    if any(w in q_l for w in ("tenure", "how long", "new")):
        facts["median_tenure_churners"] = float(df.loc[df.churn_flag == 1, "tenure"].median())
        facts["median_tenure_stayers"] = float(df.loc[df.churn_flag == 0, "tenure"].median())

    if any(w in q_l for w in ("top", "worst", "highest", "risk", "save")):
        scores_path = OUT / "risk_scores.csv"
        if scores_path.exists():
            scores = pd.read_csv(scores_path)
            facts["top5_by_expected_value"] = scores.nlargest(
                5, "expected_value")[
                    ["customerID", "p_churn", "expected_value"]].to_dict("records")
        else:
            facts["risk_note"] = ("risk_scores.csv not found — run "
                                  "02_model_roi.py to enable ranked save-list answers")

    if any(w in q_l for w in ("roi", "cost", "budget", "program")):
        facts["roi_scenario"] = json.loads((OUT / "model_eval.json").read_text())

    # headline metrics always included (cheap, always true)
    n = len(df); ch = int(df.churn_flag.sum())
    facts["headline"] = {
        "total_customers": n, "churners": ch,
        "churn_rate": round(ch / n, 4),
        "mrr_at_risk": float(df.loc[df.churn_flag == 1, "MonthlyCharges"].sum()),
    }
    return {k: v for k, v in facts.items()}


def offline_answer(f: dict) -> str:
    lines = ["(offline engine — every number below recomputed from the csv)", ""]
    if "by_contract" in f:
        b = f["by_contract"]
        lines.append("Churn by contract — " + "; ".join(
            f"{k}: {v['churn_rate']:.1%} of {v['customers']:,}" for k, v in b.items()))
    if "by_payment" in f:
        lines.append("Churn by payment — " + "; ".join(
            f"{k}: {v:.1%}" for k, v in f["by_payment"].items()))
    if "by_internet" in f:
        b = f["by_internet"]
        lines.append("Churn by internet service — " + "; ".join(
            f"{k}: {v['churn_rate']:.1%} ({v['churners']:,} churners of {v['customers']:,})"
            for k, v in b.items()))
    if "median_tenure_churners" in f:
        lines.append(f"Median tenure — churners {f['median_tenure_churners']:.0f} mo vs "
                     f"stayers {f['median_tenure_stayers']:.0f} mo")
    if "top5_by_expected_value" in f:
        lines.append("Top-5 by expected value (p_churn × monthly charge):")
        lines += [f"  {r['customerID']} — p={r['p_churn']:.2f}, ${r['expected_value']:.0f}/mo at risk"
                  for r in f["top5_by_expected_value"]]
    if "risk_note" in f:
        lines.append(f"  ({f['risk_note']})")
    if "roi_scenario" in f:
        r = f["roi_scenario"]
        lines += [f"ROI scenario (assumptions: {', '.join(r['assumptions'])}):",
                  f"  ${r['program_cost_usd']:,.0f} cost → ${r['mrr_saved_12m_usd']:,.0f} "
                  f"retained 12-mo → {r['roi_12m']:.1f}x ROI"]
    h = f["headline"]
    lines += ["", f"Overall: {h['churners']:,} of {h['total_customers']:,} churn "
              f"({h['churn_rate']:.1%}); ${h['mrr_at_risk']:,.0f} MRR at risk."]
    return "\n".join(lines)


def llm_answer(question: str, f: dict) -> str | None:
    import urllib.request
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    body = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content":
                      "You are a churn analytics assistant. Use ONLY the JSON of "
                      "verified, precomputed facts below. Do not compute, estimate or "
                      "invent any number. Answer concisely (max 12 lines).\n\n"
                      f"Question: {question}\n\nVerified facts (JSON): "
                      + json.dumps(f, default=str)}],
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


# ------------------------------- REPL --------------------------------------

HELP = """Questions I can answer (all computed live from the data):
  churn by contract / payment / service · median tenure of churners
  top 5 customers by churn risk · the retention ROI · anything about segments
Type 'quit' to exit."""


def main() -> None:
    df = pd.read_csv(PROJECT / "data" / "processed" / "telco_clean.csv")

    if len(sys.argv) > 1:  # one-shot mode: 06_chat.py "your question"
        f = compute(df, " ".join(sys.argv[1:]))
        ans = None
        if os.environ.get("GROQ_API_KEY"):
            try:
                ans = llm_answer(" ".join(sys.argv[1:]), f)
            except Exception as exc:  # noqa: BLE001 — network/API, offline is the fallback
                print(f"(LLM call failed: {exc} — offline fallback)")
        print(ans if ans else offline_answer(f))
        return

    print(HELP)
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in {"quit", "exit", "q"}:
            break
        f = compute(df, q)
        ans = None
        if os.environ.get("GROQ_API_KEY"):
            try:
                ans = llm_answer(q, f)
            except Exception as exc:  # noqa: BLE001
                print(f"(LLM call failed: {exc} — offline fallback)")
        print(ans if ans else offline_answer(f))
        print()


if __name__ == "__main__":
    main()
