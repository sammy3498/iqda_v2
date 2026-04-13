import json
import re
import pandas as pd
from src.topic_mapper import detect_subtopic

def norm(s):
    return re.sub(r"\s+", " ", str(s).strip())

def safe_json_list(x):
    try:
        if pd.isna(x):
            return []
    except:
        pass
    if isinstance(x, list):
        return x
    if not x:
        return []
    try:
        val = json.loads(x)
        return val if isinstance(val, list) else []
    except:
        return []

def word_list(text):
    return re.findall(r"\b\w+\b", norm(text).lower())

def sentence_count(text):
    parts = re.split(r"[.!?]+", norm(text))
    parts = [p for p in parts if p.strip()]
    return max(1, len(parts))

def readability_proxy(text):
    words = word_list(text)
    if not words:
        return 0.0
    avg_word_len = sum(len(w) for w in words) / len(words)
    avg_sent_len = len(words) / sentence_count(text)
    return round(avg_word_len + (avg_sent_len / 4), 2)

def extract_numeric_features(text):
    t = norm(text)
    return {
        "number_count": len(re.findall(r"\b\d+(\.\d+)?\b", t)),
        "symbol_count": len(re.findall(r"[\+\-\*/=<>\^%]", t)),
        "unit_count": len(re.findall(r"\b(kg|g|m|cm|km|s|min|hour|n|j|w|m/s|m/s2|m/s\^2)\b", t.lower()))
    }

def detect_question_form(text):
    q = norm(text).lower()

    if any(x in q for x in ["define", "list", "name", "identify"]):
        return "direct_recall"

    if any(x in q for x in ["derive", "show that", "obtain"]):
        if any(y in q for y in ["explain", "role of", "clearly explain"]):
            return "derivation_explanation"
        return "derivation"

    if any(x in q for x in [
        "find", "calculate", "compute", "solve",
        "what force", "what is the force",
        "how fast", "how much", "what acceleration",
        "determine"
    ]):
        if count_subquestions(q) >= 3 or count_stage_cues(q) >= 2:
            return "multi_stage_numeric"
        return "numeric_application"

    if any(x in q for x in ["explain", "describe", "state"]):
        return "concept_explanation"

    if any(x in q for x in ["compare", "differentiate", "analyze"]):
        return "analytical"

    if any(x in q for x in ["infer", "imply", "suggest", "conclude"]):
        return "inference"

    return "general"

def detect_cognitive_level(text):
    q = norm(text).lower()

    if any(x in q for x in ["define", "list", "name", "identify"]):
        return "recall"
    if any(x in q for x in ["explain", "describe", "state", "summarize"]):
        return "understand"
    if any(x in q for x in ["solve", "calculate", "find", "compute", "use", "determine"]):
        return "apply"
    if any(x in q for x in ["analyze", "compare", "differentiate", "infer"]):
        return "analyze"
    if any(x in q for x in ["justify", "evaluate", "criticize"]):
        return "evaluate"
    if any(x in q for x in ["design", "create", "propose", "derive", "obtain", "show that"]):
        return "create"

    return "apply"

def count_subquestions(text):
    t = norm(text).lower()

    trigger_count = 0
    triggers = [
        "derive", "determine", "find", "calculate", "compute",
        "obtain", "show that", "explain", "justify", "state"
    ]
    for trig in triggers:
        trigger_count += len(re.findall(r"\b" + re.escape(trig) + r"\b", t))

    line_parts = [x.strip() for x in str(text).split("\n") if x.strip()]
    enumerated = sum(
        1 for x in line_parts
        if re.match(r"^(\(?[ivx]+\)?\.?|\(?\d+\)?\.?|[a-z]\))", x.strip().lower())
    )

    return max(trigger_count, enumerated, 1)

def count_stage_cues(text):
    t = norm(text).lower()
    cues = [
        "before collision",
        "after the collision",
        "immediately after",
        "at the bottom",
        "released from rest",
        "moves on",
        "climbs up",
        "throughout the motion",
        "each stage",
        "just before",
        "then",
        "continues moving"
    ]
    return sum(1 for c in cues if c in t)

def count_advanced_physics_cues(text):
    t = norm(text).lower()
    cues = [
        "moment of inertia",
        "rotational kinetic energy",
        "rolls down without slipping",
        "rolling without slipping",
        "elastic collision",
        "conservation of mechanical energy",
        "conservation of linear momentum",
        "translational velocity",
        "rotational speed",
        "inclined plane",
        "inclination",
        "rough surface",
        "rotational motion",
        "collision"
    ]
    return sum(1 for c in cues if c in t)

def count_principle_cues(text):
    t = norm(text).lower()
    groups = {
        "energy": ["mechanical energy", "kinetic energy", "potential energy", "conservation of mechanical energy"],
        "momentum": ["linear momentum", "conservation of linear momentum", "momentum"],
        "rotation": ["rotational motion", "moment of inertia", "rotational kinetic energy", "rotation"],
        "collision": ["elastic collision", "inelastic collision", "collision"],
        "rolling": ["rolling without slipping", "without slipping", "no slipping"],
        "incline": ["inclined plane", "incline", "inclination"]
    }
    cnt = 0
    for vals in groups.values():
        if any(v in t for v in vals):
            cnt += 1
    return cnt

def count_symbolic_variables(text):
    raw = str(text)

    found = set()

    # quantity-name followed by explicit variable symbol
    pats = [
        r"\bmass\s+([A-Za-zθωαβφλ])\b",
        r"\bradius\s+([A-Za-zθωαβφλ])\b",
        r"\bheight\s+([A-Za-zθωαβφλ])\b",
        r"\binclination\s+([A-Za-zθωαβφλ])\b",
        r"\bspeed\s+([A-Za-zθωαβφλ])\b",
        r"\bvelocity\s+([A-Za-zθωαβφλ])\b",
        r"\bforce\s+([A-Za-zθωαβφλ])\b",
        r"\bacceleration\s+([A-Za-zθωαβφλ])\b"
    ]
    for p in pats:
        found.update(re.findall(p, raw))

    # greek symbols / greek words
    for tok in ["theta", "alpha", "beta", "omega", "phi", "lambda"]:
        if re.search(r"\b" + tok + r"\b", raw.lower()):
            found.add(tok)

    for ch in raw:
        if ch in "θωαβφλΘΩ":
            found.add(ch)

    return len(found)

def count_task_variety(text):
    t = norm(text).lower()
    verbs = {
        "derive": "derive",
        "determine": "determine",
        "find": "find",
        "calculate": "calculate",
        "compute": "compute",
        "obtain": "obtain",
        "explain": "explain",
        "justify": "justify",
        "show that": "show"
    }
    seen = set()
    for k, v in verbs.items():
        if k in t:
            seen.add(v)
    return len(seen)

def has_explanation_requirement(text):
    t = norm(text).lower()
    return int(any(x in t for x in [
        "explain the role of",
        "clearly explain",
        "explain the role",
        "justify",
        "explain each stage"
    ]))

def build_feature_record(row):
    qtext = norm(row.get("question_text", ""))
    ptext = norm(row.get("passage_text", ""))
    options = safe_json_list(row.get("options_json", "[]"))
    givens = safe_json_list(row.get("givens_json", "[]"))
    unknowns = safe_json_list(row.get("unknowns_json", "[]"))
    methods = safe_json_list(row.get("method_tags_json", "[]"))

    full_text = qtext
    if ptext:
        full_text = ptext + " " + qtext
    if options:
        full_text += " " + " ".join(options)

    field = row.get("field", "")
    subject = row.get("subject", "")
    topic = row.get("topic", "")
    subtopic = row.get("subtopic", "")

    if not subtopic:
        subtopic = detect_subtopic(field, topic, qtext + " " + ptext)

    nums = extract_numeric_features(full_text)
    words = word_list(full_text)

    return {
        "question_id": row.get("question_id", ""),
        "question_type": row.get("question_type", ""),
        "field": field,
        "subject": subject,
        "topic": topic,
        "subtopic": subtopic,
        "education_level": row.get("education_level", ""),
        "difficulty_score": row.get("difficulty_score", 0),
        "question_text": qtext,
        "passage_text": ptext,
        "options_json": json.dumps(options, ensure_ascii=False),
        "givens_json": json.dumps(givens, ensure_ascii=False),
        "unknowns_json": json.dumps(unknowns, ensure_ascii=False),
        "method_tags_json": json.dumps(methods, ensure_ascii=False),
        "full_text": full_text,
        "word_count": len(words),
        "sentence_count": sentence_count(full_text),
        "readability_proxy": readability_proxy(full_text),
        "number_count": nums["number_count"],
        "symbol_count": nums["symbol_count"],
        "unit_count": nums["unit_count"],
        "options_count": len(options),
        "passage_word_count": len(word_list(ptext)),
        "question_form": detect_question_form(qtext),
        "cognitive_level": detect_cognitive_level(qtext),
        "subquestion_count": count_subquestions(qtext),
        "stage_count": count_stage_cues(qtext),
        "advanced_physics_cue_count": count_advanced_physics_cues(qtext),
        "principle_cue_count": count_principle_cues(qtext),
        "symbolic_variable_count": count_symbolic_variables(qtext),
        "task_variety_count": count_task_variety(qtext),
        "explanation_required": has_explanation_requirement(qtext),
    }

def build_feature_dataframe(df):
    rows = [build_feature_record(r) for _, r in df.iterrows()]
    return pd.DataFrame(rows)