import pandas as pd
from sklearn.model_selection import train_test_split

FEATURES = [
    "Task_Duration_Days",
    "Labor_Required",
    "Equipment_Units",
    "Start_Constraint",
    "Risk_Level",
    "Resource_Constraint_Score",
    "Site_Constraint_Score",
    "Dependency_Count",
]
TARGET = "Material_Cost_USD"

RISK_MAP = {"Low": 0, "Medium": 1, "High": 2}


def load_and_split(csv_path: str, random_state: int = 42):
    """
    70% train / 15% val / 15% holdout

    Returns
    -------
    X_train, X_val, X_holdout, y_train, y_val, y_holdout
    """
    df = pd.read_csv(csv_path)
    df["Risk_Level"] = df["Risk_Level"].map(RISK_MAP)

    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in dataset: {missing}")

    X = df[FEATURES]
    y = df[TARGET]

    # Step 1: split off 15% holdout  →  85% trainval / 15% holdout
    X_trainval, X_holdout, y_trainval, y_holdout = train_test_split(
        X, y, test_size=0.15, random_state=random_state
    )

    # Step 2: split trainval into 70% train / 15% val  (15/85 ≈ 0.1765)
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=round(15 / 85, 4), random_state=random_state
    )

    return X_train, X_val, X_holdout, y_train, y_val, y_holdout
