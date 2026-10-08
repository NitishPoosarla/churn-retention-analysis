"""01-telco-churn — 02_model_roi.py — interpretable model + costed retention ROI."""
from pathlib import Path
import json

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "outputs"

# Written-down ROI assumptions (also stated in README):
COST_PER_CONTACT = 50.0      # $ outreach cost for each contacted customer
SAVE_RATE = 0.10             # 10% of contacted customers are successfully saved
BUDGET = 10_000.0            # total retention program budget ($)

DROP = ["customerID", "Churn", "churn_flag", "tenure_bucket"]
CATS = ["gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
        "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
        "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
        "PaperlessBilling", "PaymentMethod"]
NUMS = ["tenure", "MonthlyCharges", "TotalCharges"]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    df = pd.read_csv(PROJECT / "data" / "processed" / "telco_clean.csv")

    y = df["churn_flag"]
    X = pd.concat(
        [df[NUMS],
         pd.get_dummies(df[CATS], drop_first=True)],
        axis=1,
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)

    model = LogisticRegression(max_iter=2000)
    model.fit(X_train, y_train)

    auc = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))

    # Score EVERY customer, rank by expected value = p_churn * monthly_charges
    df["p_churn"] = model.predict_proba(X)[:, 1].round(4)
    df["expected_value"] = (df["p_churn"] * df["MonthlyCharges"]).round(2)
    scores = df[["customerID", "p_churn", "Contract", "tenure",
                 "MonthlyCharges", "expected_value"]].sort_values(
        "expected_value", ascending=False)
    scores.to_csv(OUT / "risk_scores.csv", index=False)

    # Costed program: pick highest expected_value customers within budget
    n_contacts = int(BUDGET // COST_PER_CONTACT)
    picked = scores.head(n_contacts)
    total_mrr_saved = float(
        (picked["expected_value"] * SAVE_RATE).sum())  # $/month retained
    program = {
        "auc": round(auc, 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "assumptions": [
            f"outreach cost per contacted customer = ${COST_PER_CONTACT:.0f}",
            f"save rate = {SAVE_RATE:.0%} of contacted customers",
            f"program budget = ${BUDGET:,.0f} -> {n_contacts} contacts",
        ],
        "program_cost_usd": float(n_contacts * COST_PER_CONTACT),
        "mrr_saved_per_month_usd": round(total_mrr_saved, 2),
        "mrr_saved_12m_usd": round(total_mrr_saved * 12, 2),
        "roi_12m": round(total_mrr_saved * 12 / (n_contacts * COST_PER_CONTACT), 2),
    }
    (OUT / "model_eval.json").write_text(json.dumps(program, indent=2))

    print(json.dumps(program, indent=2))
    print(f"\nTop-5 save list:\n{picked[['customerID', 'p_churn', 'expected_value']].head().to_string(index=False)}")


if __name__ == "__main__":
    main()
