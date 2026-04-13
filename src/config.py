from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"

for p in [RAW, INTERIM, PROCESSED]:
    p.mkdir(parents=True, exist_ok=True)

MASTER_CSV = PROCESSED / "iqda_master_dataset.csv"
SAMPLE_CSV = PROCESSED / "iqda_master_dataset_sample.csv"