import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import MASTER_CSV
from src.feature_extractor import build_feature_dataframe, build_feature_record


def safe_list(x):
    if isinstance(x, list):
        return x
    if not x:
        return []
    try:
        v = json.loads(x)
        return v if isinstance(v, list) else []
    except:
        return []


def jaccard(a, b):
    a = set(safe_list(a))
    b = set(safe_list(b))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class RetrievalEngine:
    def __init__(self, csv_path=MASTER_CSV):
        self.raw_df = pd.read_csv(csv_path, low_memory=False)
        self.feat_df = build_feature_dataframe(self.raw_df)

        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words="english"
        )
        self.text_mat = self.vectorizer.fit_transform(self.feat_df["full_text"].astype(str))

    def filter_candidates(self, query_feat, top_n=3000):
        qtype = str(query_feat.get("question_type", "")).strip()
        field = str(query_feat.get("field", "")).strip()
        topic = str(query_feat.get("topic", "")).strip()

        base = self.feat_df.copy()

        # first try same type
        same_type = base[base["question_type"] == qtype].copy()

        # if very few or none, fall back to whole dataset
        df = same_type if len(same_type) >= 20 else base.copy()

        # then prefer same topic
        if topic and topic != "general":
            temp = df[df["topic"] == topic].copy()
            if len(temp) >= 20:
                df = temp
            else:
                temp = df[df["field"] == field].copy()
                if len(temp) >= 20:
                    df = temp
        else:
            temp = df[df["field"] == field].copy()
            if len(temp) >= 20:
                df = temp

        # last-resort fallback
        if len(df) == 0:
            df = base.copy()

        if len(df) > top_n:
            df = df.sample(top_n, random_state=42)

        return df

    def score_candidates(self, query_feat, cand_df, top_k=10):
        out_cols = [
            "row_idx", "similarity", "semantic_similarity", "field", "topic",
            "subtopic", "education_level", "difficulty_score",
            "question_text", "question_type", "source_dataset"
        ]

        if cand_df is None or len(cand_df) == 0:
            return pd.DataFrame(columns=out_cols)

        query_text = [str(query_feat["full_text"])]
        qvec = self.vectorizer.transform(query_text)

        idxs = cand_df.index.tolist()
        if len(idxs) == 0:
            return pd.DataFrame(columns=out_cols)

        cmat = self.text_mat[idxs]
        sem_scores = cosine_similarity(qvec, cmat).flatten()

        final_rows = []

        for row_idx, sem in zip(idxs, sem_scores):
            row = self.feat_df.loc[row_idx]

            topic_sim = 1.0 if query_feat["topic"] == row["topic"] else 0.0
            subtopic_sim = 1.0 if query_feat["subtopic"] == row["subtopic"] and query_feat["subtopic"] != "" else 0.0
            field_sim = 1.0 if query_feat["field"] == row["field"] else 0.0
            qtype_sim = 1.0 if query_feat["question_type"] == row["question_type"] else 0.0
            qform_sim = 1.0 if query_feat["question_form"] == row["question_form"] else 0.0
            cog_sim = 1.0 if query_feat["cognitive_level"] == row["cognitive_level"] else 0.0

            givens_sim = jaccard(query_feat["givens_json"], row["givens_json"])
            unknowns_sim = jaccard(query_feat["unknowns_json"], row["unknowns_json"])
            methods_sim = jaccard(query_feat["method_tags_json"], row["method_tags_json"])

            options_gap = abs(int(query_feat["options_count"]) - int(row["options_count"]))
            options_sim = max(0.0, 1.0 - 0.25 * options_gap)

            score = (
                0.24 * sem +
                0.12 * topic_sim +
                0.12 * subtopic_sim +
                0.08 * field_sim +
                0.06 * qtype_sim +
                0.16 * givens_sim +
                0.16 * unknowns_sim +
                0.08 * methods_sim +
                0.04 * qform_sim +
                0.03 * cog_sim +
                0.01 * options_sim
            )

            final_rows.append({
                "row_idx": row_idx,
                "similarity": round(float(score), 4),
                "semantic_similarity": round(float(sem), 4),
                "field": row["field"],
                "topic": row["topic"],
                "subtopic": row["subtopic"],
                "education_level": row["education_level"],
                "difficulty_score": float(row["difficulty_score"]),
                "question_text": row["question_text"],
                "question_type": row["question_type"],
                "source_dataset": row["question_id"].split("_")[0]
            })

        out = pd.DataFrame(final_rows)
        out = out.sort_values("similarity", ascending=False).head(top_k).reset_index(drop=True)
        return out

    def retrieve(self, query_dict, top_k=10):
        query_feat = build_feature_record(query_dict)
        cand_df = self.filter_candidates(query_feat)
        return self.score_candidates(query_feat, cand_df, top_k=top_k), query_feat