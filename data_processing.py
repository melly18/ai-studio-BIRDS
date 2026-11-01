import pandas as pd


def mask_pii_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the payment data with cardholder PII redacted."""
    masked_df = df.copy()
    if "card_holder_pii" in masked_df.columns:
        masked_df["card_holder_pii"] = "[REDACTED]"
    return masked_df