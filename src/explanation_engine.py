import numpy as np
from src.difficulty_engine import DifficultyEngine

def level_phrase(level):
    m = {
        "elementary": "typically seen at elementary-school level",
        "middle school": "typically seen at middle-school level",
        "high school": "typically seen at high-school level",
        "undergraduate": "typically seen at undergraduate level",
        "postgraduate": "typically seen at postgraduate level",
        "doctoral": "typically seen at doctoral level",
        "unknown": "education level could not be estimated confidently"
    }
    return m.get(str(level).lower(), f"typically seen around {level} level")

def band_meaning(score, band):
    if band == "Very easy":
        return "This looks very straightforward and mostly recall-based."
    if band == "Easy":
        return "This looks fairly direct with limited reasoning burden."
    if band == "Moderate":
        return "This needs some understanding or application, but is not deeply multi-step."
    if band == "Hard":
        return "This likely needs stronger reasoning, interpretation, or multi-step solving."
    return "This appears to be among the more demanding questions in this area."

def confidence_from_matches(res_df):
    if len(res_df) == 0:
        return 0.25

    sims = res_df["similarity"].astype(float).values
    diffs = res_df["difficulty_score"].astype(float).values

    top_sim = float(np.max(sims))
    sim_part = min(max(top_sim, 0.0), 1.0)

    if len(diffs) > 1:
        spread = float(np.std(diffs))
        spread_part = max(0.0, 1.0 - min(spread / 3.0, 1.0))
    else:
        spread_part = 0.7

    conf = 0.7 * sim_part + 0.3 * spread_part
    return round(float(np.clip(conf, 0.0, 1.0)), 3)

def question_type_text(qtype):
    m = {
        "standard": "Standard question",
        "mcq": "MCQ",
        "comprehension": "Comprehension question"
    }
    return m.get(str(qtype).lower(), str(qtype))

def build_match_reason(query_feat, top_matches):
    if len(top_matches) == 0:
        return ["No close stored questions were found, so the score leaned more on intrinsic complexity."]

    top = top_matches.iloc[0]
    lines = []

    lines.append(
        f"The strongest match was a {top['education_level']} {top['field']} question on '{top['topic']}'."
    )

    if str(query_feat.get("subtopic", "")).strip():
        lines.append(
            f"Detected subtopic: {query_feat['subtopic']}."
        )

    qform = str(query_feat.get("question_form", "general")).replace("_", " ")
    cog = str(query_feat.get("cognitive_level", "apply")).replace("_", " ")
    lines.append(f"The question form looks like {qform}, and the cognitive level looks like {cog}.")

    givens = str(query_feat.get("givens_json", "[]"))
    unknowns = str(query_feat.get("unknowns_json", "[]"))

    if givens != "[]":
        lines.append(f"Detected givens: {givens}.")
    if unknowns != "[]":
        lines.append(f"Detected target/unknowns: {unknowns}.")

    wc = int(query_feat.get("word_count", 0))
    pwords = int(query_feat.get("passage_word_count", 0))
    opts = int(query_feat.get("options_count", 0))

    if pwords > 0:
        lines.append(f"The passage contributes {pwords} words of reading load.")
    else:
        lines.append(f"The question wording is short to medium length at about {wc} words.")

    if opts > 0:
        lines.append(f"It includes {opts} answer options, so option elimination also matters.")

    return lines

def build_score_reason(out):
    lines = []

    lines.append(
        f"Retrieved-neighbor anchor score: {out['retrieval_score']}."
    )
    lines.append(
        f"Intrinsic complexity score: {out['intrinsic_score']}."
    )
    lines.append(
        f"Final blend used lambda = {out['blend_lambda']}, meaning retrieval was weighted more when close matches existed."
    )

    band = out["difficulty_band"]
    lines.append(band_meaning(out["difficulty_score"], band))

    return lines

def summarize_matches(top_matches):
    rows = []
    if len(top_matches) == 0:
        return rows

    for _, r in top_matches.iterrows():
        rows.append({
            "similarity": float(r["similarity"]),
            "difficulty_score": float(r["difficulty_score"]),
            "field": str(r["field"]),
            "topic": str(r["topic"]),
            "subtopic": str(r.get("subtopic", "")),
            "education_level": str(r["education_level"]),
            "question_text": str(r["question_text"])
        })
    return rows

class ExplanationEngine:
    def __init__(self):
        self.diff_engine = DifficultyEngine()

    def analyze(self, query_dict, top_k=5):
        out = self.diff_engine.analyze(query_dict, top_k=top_k)

        qfeat = out["query_features"]
        top_matches = out["top_matches"]

        conf = confidence_from_matches(top_matches)

        summary = (
            f"{question_type_text(qfeat.get('question_type', ''))} in "
            f"{out['predicted_field']} → {qfeat.get('topic', 'general topic')}"
        )

        if str(qfeat.get("subtopic", "")).strip():
            summary += f" → {qfeat['subtopic']}"

        explanation_lines = []
        explanation_lines.append(
            f"Difficulty score: {out['difficulty_score']}/10 ({out['difficulty_band']})."
        )
        explanation_lines.append(
            f"Likely field: {out['predicted_field']}."
        )
        explanation_lines.append(
            f"Likely education level: {out['predicted_level']} ({level_phrase(out['predicted_level'])})."
        )
        explanation_lines.append(
            f"Confidence: {conf}."
        )
        explanation_lines.append("")

        explanation_lines.extend(build_match_reason(qfeat, top_matches))
        explanation_lines.append("")
        explanation_lines.extend(build_score_reason(out))

        return {
            "difficulty_score": out["difficulty_score"],
            "difficulty_band": out["difficulty_band"],
            "score_meaning": band_meaning(out["difficulty_score"], out["difficulty_band"]),
            "predicted_field": out["predicted_field"],
            "predicted_level": out["predicted_level"],
            "topic": qfeat.get("topic", ""),
            "subtopic": qfeat.get("subtopic", ""),
            "question_type": qfeat.get("question_type", ""),
            "confidence": conf,
            "summary": summary,
            "query_features": qfeat,
            "top_matches": summarize_matches(top_matches),
            "explanation_lines": explanation_lines
        }