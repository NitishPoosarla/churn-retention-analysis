"""01-telco-churn — 01_prepare_analysis.py — clean, segment, and compute verified KPIs."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
RAW = PROJECT / "data" / "raw" / "Telco-Customer-Churn.csv"
OUT = PROJECT / "outputs"
PROCESSED = PROJECT / "data" / "processed"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    charts = OUT / "charts"
    charts.mkdir(exist_ok=True)

    df = pd.read_csv(RAW)

    # --- Clean: TotalCharges has 11 blank strings (new customers, tenure 0) ---
    blank_total = int((df["TotalCharges"].astype(str).str.strip() == "").sum())
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    blank_tenure = int(df.loc[df["TotalCharges"].isna(), "tenure"].eq(0).sum())
    df["TotalCharges"] = df["TotalCharges"].fillna(0.0)
    df["churn_flag"] = (df["Churn"] == "Yes").astype(int)
    df.to_csv(PROCESSED / "telco_clean.csv", index=False)
    print(f"Cleaned: {len(df)} rows; {blank_total} blank TotalCharges "
          f"({blank_tenure} with tenure=0 -> set to 0)")

    # --- Verified KPIs ---
    n = len(df)
    churners = int(df["churn_flag"].sum())
    churn_rate = churners / n
    mrr_at_risk = float(df.loc[df["churn_flag"] == 1, "MonthlyCharges"].sum())
    totalch_at_risk = float(df.loc[df["churn_flag"] == 1, "TotalCharges"].sum())
    ten_med_churners = float(df.loc[df["churn_flag"] == 1, "tenure"].median())
    ten_med_stay = float(df.loc[df["churn_flag"] == 0, "tenure"].median())

    kpis = {
        "total_customers": n,
        "churners": churners,
        "churn_rate": round(churn_rate, 4),
        "mrr_at_risk_usd": round(mrr_at_risk, 2),
        "total_charges_at_risk_usd": round(totalch_at_risk, 2),
        "median_tenure_months_churners": ten_med_churners,
        "median_tenure_months_stayers": ten_med_stay,
        "blank_totalcharges_fixed": blank_total,
    }

    # --- Segment tables ---
    def seg_table(col: str) -> pd.DataFrame:
        g = df.groupby(col).agg(
            customers=("churn_flag", "size"),
            churners=("churn_flag", "sum"),
            churn_rate=("churn_flag", "mean"),
            mrr_at_risk=("MonthlyCharges",
                         lambda s: s[df.loc[s.index, "churn_flag"] == 1].sum()),
        ).reset_index()
        g["churn_rate"] = g["churn_rate"].round(4)
        g["mrr_at_risk"] = g["mrr_at_risk"].round(2)
        return g.sort_values("churn_rate", ascending=False)

    tables = {
        "seg_contract.csv": "Contract",
        "seg_payment.csv": "PaymentMethod",
        "seg_services.csv": "MultipleLines",
    }
    for fname, col in tables.items():
        seg_table(col).to_csv(OUT / fname, index=False)

    # Tenure buckets
    bins = [0, 6, 12, 24, 48, 73]
    labels = ["0-6m", "7-12m", "13-24m", "25-48m", "49m+"]
    df["tenure_bucket"] = pd.cut(df["tenure"], bins=bins, labels=labels,
                                 include_lowest=True)
    seg_table("tenure_bucket").to_csv(OUT / "seg_tenure.csv", index=False)
    df.to_csv(PROCESSED / "telco_clean.csv", index=False)  # include bucket col

    (OUT / "kpis.json").write_text(json.dumps(kpis, indent=2))

    # --- Charts ---
    contract = seg_table("Contract")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(contract["Contract"], contract["churn_rate"] * 100,
           color=["#d9534f", "#f0ad4e", "#5cb85c"])
    ax.set_ylabel("Churn rate (%)")
    ax.set_title("Churn rate by contract type")
    fig.tight_layout()
    fig.savefig(charts / "churn_by_contract.png", dpi=120)
    plt.close(fig)

    pay = seg_table("PaymentMethod")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(pay["PaymentMethod"], pay["churn_rate"] * 100, color="#4b7bec")
    ax.set_xlabel("Churn rate (%)")
    ax.set_title("Churn rate by payment method")
    fig.tight_layout()
    fig.savefig(charts / "churn_by_payment.png", dpi=120)
    plt.close(fig)

    ten = seg_table("tenure_bucket")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(ten["tenure_bucket"].astype(str), ten["churn_rate"] * 100,
           color="#8e44ad")
    ax.set_ylabel("Churn rate (%)")
    ax.set_title("Churn rate by tenure bucket")
    fig.tight_layout()
    fig.savefig(charts / "churn_by_tenure.png", dpi=120)
    plt.close(fig)

    print(json.dumps(kpis, indent=2))


if __name__ == "__main__":
    main()
