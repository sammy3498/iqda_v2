import numpy as np
from src.retrieval_engine import RetrievalEngine

LEVEL_ORDER = {
    "elementary": 1,
    "middle school": 2,
    "high school": 3,
    "undergraduate": 4,
    "postgraduate": 5,
    "doctoral": 6
}

def difficulty_band(score):
    if score <= 2.5:
        return "Very easy"
    if score <= 4.0:
        return "Easy"
    if score <= 6.0:
        return "Moderate"
    if score <= 8.0:
        return "Hard"
    return "Very hard"

def weighted_neighbor_score(res_df):
    if len(res_df) == 0:
        return 5.0

    df = res_df.copy()
    df = df[df["similarity"] >= 0.53].copy()

    if len(df) == 0:
        df = res_df.head(3).copy()

    sims = df["similarity"].astype(float).values
    diffs = df["difficulty_score"].astype(float).values

    w = np.exp(5 * sims)
    return float(np.sum(w * diffs) / np.sum(w))

def intrinsic_complexity(qfeat):
    score = 1.0

    wc = float(qfeat["word_count"])
    sc = float(qfeat["sentence_count"])
    nums = float(qfeat["number_count"])
    syms = float(qfeat["symbol_count"])
    units = float(qfeat["unit_count"])
    opts = float(qfeat["options_count"])
    pwords = float(qfeat["passage_word_count"])

    cog = str(qfeat.get("cognitive_level", "")).lower()
    qform = str(qfeat.get("question_form", "")).lower()
    qtype = str(qfeat.get("question_type", "")).lower()
    givens = str(qfeat.get("givens_json", ""))
    unknowns = str(qfeat.get("unknowns_json", ""))

    subqs = int(qfeat.get("subquestion_count", 1))
    stages = int(qfeat.get("stage_count", 0))
    adv_phys = int(qfeat.get("advanced_physics_cue_count", 0))
    principles = int(qfeat.get("principle_cue_count", 0))
    sym_vars = int(qfeat.get("symbolic_variable_count", 0))
    task_variety = int(qfeat.get("task_variety_count", 1))
    explain_req = int(qfeat.get("explanation_required", 0))
    subtopic = str(qfeat.get("subtopic", "")).lower()

    if wc <= 10:
        score += 0.5
    elif wc <= 20:
        score += 1.0
    elif wc <= 40:
        score += 1.8
    elif wc <= 80:
        score += 2.6
    elif wc <= 150:
        score += 3.6
    else:
        score += 4.8

    if sc >= 3:
        score += 0.4
    if sc >= 5:
        score += 0.6
    if sc >= 8:
        score += 0.8

    score += min(nums * 0.12, 1.0)
    score += min(syms * 0.08, 0.7)
    score += min(units * 0.10, 0.6)

    if opts >= 4:
        score += 0.3
    if opts >= 5:
        score += 0.2

    if pwords >= 80:
        score += 0.8
    if pwords >= 180:
        score += 0.8

    cog_map = {
        "recall": 0.6,
        "understand": 1.0,
        "apply": 1.8,
        "analyze": 2.8,
        "evaluate": 3.5,
        "create": 4.2
    }
    score += cog_map.get(cog, 1.5)

    qform_map = {
        "direct_recall": 0.3,
        "concept_explanation": 0.8,
        "numeric_application": 1.2,
        "analytical": 1.8,
        "inference": 1.6,
        "derivation": 2.4,
        "derivation_explanation": 2.8,
        "multi_stage_numeric": 3.0,
        "general": 0.8
    }
    score += qform_map.get(qform, 0.8)

    if qtype == "standard":
        if subqs >= 2:
            score += 0.8
        if subqs >= 4:
            score += 1.2
        if subqs >= 6:
            score += 1.4

        if stages >= 2:
            score += 0.8
        if stages >= 4:
            score += 1.0

        score += min(adv_phys * 0.32, 2.4)
        score += min(principles * 0.45, 2.2)
        score += min(sym_vars * 0.22, 1.3)
        score += min(max(task_variety - 1, 0) * 0.30, 1.2)

        if explain_req:
            score += 0.8

        if subtopic == "advanced_rigid_body_dynamics":
            score += 1.1
        elif subtopic == "collision_dynamics":
            score += 0.7

    if (
        qtype == "mcq" and
        qform == "numeric_application" and
        cog == "apply" and
        wc <= 20 and
        pwords == 0 and
        ("mass" in givens and "acceleration" in givens) and
        ("force" in unknowns)
    ):
        score -= 1.2

    return float(np.clip(score, 1.0, 10.0))

def intrinsic_level_estimate(qfeat):
    qtype = str(qfeat.get("question_type", "")).lower()
    qform = str(qfeat.get("question_form", "")).lower()
    subtopic = str(qfeat.get("subtopic", "")).lower()

    subqs = int(qfeat.get("subquestion_count", 1))
    stages = int(qfeat.get("stage_count", 0))
    adv_phys = int(qfeat.get("advanced_physics_cue_count", 0))
    principles = int(qfeat.get("principle_cue_count", 0))
    sym_vars = int(qfeat.get("symbolic_variable_count", 0))
    explain_req = int(qfeat.get("explanation_required", 0))
    wc = int(qfeat.get("word_count", 0))

    if qtype == "standard":
        if subtopic == "advanced_rigid_body_dynamics":
            return "undergraduate"
        if adv_phys >= 4 or principles >= 3 or sym_vars >= 3:
            return "undergraduate"
        if subqs >= 5 or stages >= 4 or qform in ["derivation", "derivation_explanation", "multi_stage_numeric"]:
            return "undergraduate"
        if explain_req and wc >= 80:
            return "undergraduate"
        if adv_phys >= 2 or subqs >= 3 or wc >= 80:
            return "high school"

    return "middle school"

def estimate_level(res_df, qfeat=None):
    if len(res_df) == 0:
        neighbor_level = "unknown"
    else:
        sims = np.exp(4 * res_df["similarity"].astype(float).values)
        levels = res_df["education_level"].astype(str).tolist()

        score_map = {}
        for lv, w in zip(levels, sims):
            score_map[lv] = score_map.get(lv, 0) + float(w)

        neighbor_level = max(score_map, key=score_map.get)

    if qfeat is None:
        return neighbor_level

    intrinsic_level = intrinsic_level_estimate(qfeat)

    nscore = LEVEL_ORDER.get(neighbor_level, 2)
    iscore = LEVEL_ORDER.get(intrinsic_level, 2)

    qtype = str(qfeat.get("question_type", "")).lower()
    adv_phys = int(qfeat.get("advanced_physics_cue_count", 0))
    subqs = int(qfeat.get("subquestion_count", 1))
    principles = int(qfeat.get("principle_cue_count", 0))
    qform = str(qfeat.get("question_form", "")).lower()

    if qtype == "standard" and (
        adv_phys >= 3 or
        principles >= 3 or
        subqs >= 4 or
        qform in ["derivation", "derivation_explanation", "multi_stage_numeric"]
    ):
        final_score = max(nscore, iscore)
    else:
        final_score = round(0.6 * nscore + 0.4 * iscore)

    for k, v in LEVEL_ORDER.items():
        if v == final_score:
            return k

    return neighbor_level

def estimate_field(res_df):
    if len(res_df) == 0:
        return "general"

    sims = np.exp(4 * res_df["similarity"].astype(float).values)
    fields = res_df["field"].astype(str).tolist()

    score_map = {}
    for fd, w in zip(fields, sims):
        score_map[fd] = score_map.get(fd, 0) + float(w)

    return max(score_map, key=score_map.get)

class DifficultyEngine:
    def __init__(self):
        self.retriever = RetrievalEngine()

    def analyze(self, query_dict, top_k=5):
        res_df, qfeat = self.retriever.retrieve(query_dict, top_k=top_k)

        d_retr = weighted_neighbor_score(res_df)
        d_intr = intrinsic_complexity(qfeat)

        qtype = str(qfeat.get("question_type", "")).lower()
        qform = str(qfeat.get("question_form", "")).lower()
        subqs = int(qfeat.get("subquestion_count", 1))
        adv_phys = int(qfeat.get("advanced_physics_cue_count", 0))
        principles = int(qfeat.get("principle_cue_count", 0))

        if len(res_df) == 0:
            lam = 0.35
        else:
            top_sim = float(res_df.iloc[0]["similarity"])
            if top_sim >= 0.80:
                lam = 0.85
            elif top_sim >= 0.65:
                lam = 0.78
            elif top_sim >= 0.50:
                lam = 0.68
            else:
                lam = 0.55

        if qtype == "standard" and (
            subqs >= 3 or
            adv_phys >= 3 or
            principles >= 3 or
            qform in ["derivation", "derivation_explanation", "multi_stage_numeric"]
        ):
            lam = min(lam, 0.28)

        final_score = lam * d_retr + (1 - lam) * d_intr
        final_score = round(float(np.clip(final_score, 1.0, 10.0)), 2)

        return {
            "difficulty_score": final_score,
            "difficulty_band": difficulty_band(final_score),
            "retrieval_score": round(float(d_retr), 2),
            "intrinsic_score": round(float(d_intr), 2),
            "blend_lambda": lam,
            "predicted_field": estimate_field(res_df),
            "predicted_level": estimate_level(res_df, qfeat),
            "query_features": qfeat,
            "top_matches": res_df
        }