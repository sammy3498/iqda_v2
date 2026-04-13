import pandas as pd
from src.config import MASTER_CSV
from src.feature_extractor import build_feature_dataframe

df = pd.read_csv(MASTER_CSV, low_memory=False)
sample = df.head(20).copy()

feat = build_feature_dataframe(sample)
print(feat.head())
print("\ncolumns:\n", feat.columns.tolist())