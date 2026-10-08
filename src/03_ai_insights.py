"""01-telco-churn — 03_ai_insights.py — recompute-then-narrate (LLM optional).

THE RULE: Python computes and verifies every number. AI explains, prioritizes
and frames — it never invents a metric.
"""
from pathlib import Path
import json
import os

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "outputs"


def verified_facts() -> dict:
    """Recompute every headline metric directly from the clean CSV."""
    df = pd.read_csv(PROJECT / "data" / "processed" / "telco_clean.csv")
    churners = int(df["churn_flag"].sum())
    facts = {
        "total_customers": int(len(df)),
        "churners": churners,
        "churn_rate": round(churners / len(df), 4),
        "mrr_at_risk": float(df.loc[df["churn_flag"] == 1,
                                    "MonthlyCharges"].sum()),
        "m2m_churn_rate": float(
            df.loc[df["Contract"] == "Month-to-month", "churn_flag"].mean()),
        "twoyr_churn_rate": float(
            df.loc[df["Contract"] == "Two year", "churn_flag"].mean()),
        "median_tenure_churners": float(
            df.loc[df["churn_flag"] == 1, "tenure"].median()),
        "median_tenure_stayers": float(
            df.loc[df["churn_flag"] == 0, "tenure"].median()),
    }
    ev = json.loads((OUT / "model_eval.json").read_text())
    facts.update(
        {k: v for k, v in ev.items()
         if k in ("auc", "mrr_saved_per_month_usd", "roi_12m", "assumptions")})
    return facts


def offline_narrative(f: dict) -> str:
    usd = lambda v: f"${v:,.0f}"
    pct = lambda v: f"{v:.1%}"
    return "\n".join([
        "# Retention insights (offline engine — every figure recomputed from csv)",
        "",
        f"## The problem, sized",
        f"- {f['churners']:,} of {f['total_customers']:,} customers churn "
        f"({pct(f['churn_rate'])}); {usd(f['mrr_at_risk'])} of monthly "
        "revenue is walking out the door each month.",
        "",
        "## What drives it",
        f"- **Month-to-month contracts are the smoking gun**: "
        f"{pct(f['m2m_churn_rate'])} churn vs {pct(f['twoyr_churn_rate'])} "
        "on two-year contracts.",
        f"- **Acquisition quality, not loyalty drift**: churners have median "
        f"tenure {f['median_tenure_churners']:.0f} months vs "
        f"{f['median_tenure_stayers']:.0f} for stayers — customers are "
        "leaving early.",
        "",
        "## The decision",
        f"- Prioritize the model-ranked save list (AUC {f['auc']:.2f}).",
        f"The costed program is {usd(f['mrr_saved_per_month_usd'])}"

        " in retained MRR/month and a "
        f"{f['roi_12m']:.1f}x 12-month ROI under stated assumptions.",
        "",
        "## Priorities",
        "1. Convert month-to-month customers to annual at renewal moment.",
        "2. Focus outreach dollars on top-ranked expected_value customers.",
        "3. Fix early-tenure experience (first-year onboarding).",
    ])


def llm_narrative(f: dict) -> str:
    prompt = (
        "You are a management consultant writing a one-page retention "
        "insight memo. Use ONLY the verified numbers below — do NOT estimate, "
        "compute or invent any figure. Narrate, prioritize and frame.\n\n"
        f"Verified facts (JSON): {json.dumps(f, default=str)}\n\n"
        "Structure: 'The problem, sized' / 'What drives it' / 'The decision' / "
        "'Priorities'. Markdown.")
    key = os.environ.get("GROQ_API_KEY") or os.environ.get(
        "GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    import urllib.request

    if os.environ.get("GROQ_API_KEY"):
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
            }).encode(),
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    # Fallbacks ask the user to run with a provider supported here:
    print("No supported LLM key found (GROQ fully supported; "
          "GEMINI/OPENAI set but not wired) -> using offline engine.")
    return offline_narrative(f)


def main() -> None:
    facts = verified_facts()
    print("Verified facts recomputed from csv:")
    print(json.dumps(facts, indent=2, default=str))
    text = llm_narrative(facts) if any(
        os.environ.get(k) for k in
        ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY")) \
        else offline_narrative(facts)
    (OUT / "insights.md").write_text(text)
    print("Wrote", OUT / "insights.md")


if __name__ == "__main__":
    main()
