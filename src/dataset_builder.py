import json
import re
import pandas as pd
from tqdm import tqdm
from datasets import load_dataset
from src.config import MASTER_CSV, SAMPLE_CSV
MASTER_COLS = [
    "question_id",
    "question_type",
    "field",
    "subject",
    "topic",
    "subtopic",
    "education_level",
    "question_text",
    "passage_text",
    "options_json",
    "answer_text",
    "answer_type",
    "givens_json",
    "unknowns_json",
    "method_tags_json",
    "cognitive_level",
    "difficulty_score",
    "difficulty_source",
    "source_dataset",
    "source_split"
]

def norm(s):
    return re.sub(r"\s+", " ", str(s).strip())

def to_json_list(x):
    if x is None:
        return "[]"
    if isinstance(x, str):
        return json.dumps([x], ensure_ascii=False)
    return json.dumps(list(x), ensure_ascii=False)

def detect_cognitive_level(q):
    ql = norm(q).lower()
    if any(w in ql for w in ["define", "list", "name", "identify"]):
        return "recall"
    if any(w in ql for w in ["explain", "describe", "summarize"]):
        return "explain"
    if any(w in ql for w in ["solve", "calculate", "find", "compute"]):
        return "apply"
    if any(w in ql for w in ["analyze", "differentiate", "compare", "infer"]):
        return "analyze"
    if any(w in ql for w in ["evaluate", "justify", "criticize"]):
        return "evaluate"
    if any(w in ql for w in ["design", "create", "propose"]):
        return "create"
    return "apply"

def detect_field_subject_topic(text):
    t = norm(text).lower()

    if any(k in t for k in ["force", "mass", "acceleration", "velocity", "motion", "gravity", "energy"]):
        field = "physics"
        subject = "mechanics"
        if any(k in t for k in ["newton", "inertia", "acceleration", "force"]):
            topic = "newtons laws"
            subtopic = "force and motion"
        else:
            topic = "mechanics"
            subtopic = ""
        return field, subject, topic, subtopic

    if any(k in t for k in ["equation", "factor", "ratio", "probability", "angle", "triangle"]):
        field = "mathematics"
        subject = "school mathematics"
        if "quadratic" in t:
            topic = "quadratic equations"
            subtopic = ""
        else:
            topic = "general mathematics"
            subtopic = ""
        return field, subject, topic, subtopic

    if any(k in t for k in ["cell", "dna", "photosynthesis", "ecosystem", "tissue"]):
        field = "biology"
        subject = "school biology"
        topic = "general biology"
        subtopic = ""
        return field, subject, topic, subtopic

    if any(k in t for k in ["main idea", "author", "tone", "passage", "paragraph", "infer", "suggests"]):
        field = "reading"
        subject = "reading comprehension"
        if any(k in t for k in ["main idea", "main purpose", "best title"]):
            topic = "reading main idea"
            subtopic = ""
        elif any(k in t for k in ["infer", "imply", "suggest"]):
            topic = "reading inference"
            subtopic = ""
        else:
            topic = "reading comprehension"
            subtopic = ""
        return field, subject, topic, subtopic

    return "general", "general", "general", ""

def extract_givens(text):
    t = norm(text).lower()
    givens = []

    if re.search(r"\b\d+(\.\d+)?\b", t):
        givens.append("numeric_values")
    if any(k in t for k in ["mass", "kg"]):
        givens.append("mass")
    if any(k in t for k in ["acceleration", "m/s", "m/s^2"]):
        givens.append("acceleration")
    if any(k in t for k in ["velocity", "speed"]):
        givens.append("velocity")
    if any(k in t for k in ["time", "second", "seconds"]):
        givens.append("time")
    return sorted(set(givens))

def extract_unknowns(text):
    t = norm(text).lower()
    unknowns = []

    if any(k in t for k in ["find force", "calculate force", "what is the force"]):
        unknowns.append("force")
    if any(k in t for k in ["find acceleration", "calculate acceleration"]):
        unknowns.append("acceleration")
    if any(k in t for k in ["find velocity", "calculate velocity", "speed of"]):
        unknowns.append("velocity")
    if any(k in t for k in ["main idea", "main purpose", "best title"]):
        unknowns.append("main_idea")
    if any(k in t for k in ["infer", "imply", "suggest"]):
        unknowns.append("inference")
    return sorted(set(unknowns))

def extract_method_tags(text, qtype):
    t = norm(text).lower()
    tags = []

    if any(k in t for k in ["define", "list", "name"]):
        tags.append("direct_recall")
    if any(k in t for k in ["explain", "describe"]):
        tags.append("concept_explanation")
    if any(k in t for k in ["calculate", "find", "solve", "compute"]):
        tags.append("formula_application")
    if any(k in t for k in ["compare", "analyze", "infer"]):
        tags.append("reasoning")
    if qtype == "comprehension":
        tags.append("passage_inference")
    if qtype == "mcq":
        tags.append("option_elimination")

    return sorted(set(tags))

def map_race_row(row, split_name, level_name, idx):
    article = norm(row["article"])
    q = norm(row["question"])
    options = [norm(x) for x in row["options"]]

    ans_raw = str(row["answer"]).strip()
    answer_index = ord(ans_raw.upper()) - ord("A")
    answer_text = options[answer_index] if 0 <= answer_index < len(options) else ""

    field, subject, topic, subtopic = detect_field_subject_topic(q + " " + article)

    education_level = "middle school" if level_name == "middle" else "high school"
    difficulty_score = 4.5 if level_name == "middle" else 6.5

    return {
        "question_id": f"race_{split_name}_{level_name}_{idx}",
        "question_type": "comprehension",
        "field": field if field != "general" else "reading",
        "subject": subject if subject != "general" else "reading comprehension",
        "topic": topic if topic != "general" else "reading comprehension",
        "subtopic": subtopic,
        "education_level": education_level,
        "question_text": q,
        "passage_text": article,
        "options_json": to_json_list(options),
        "answer_text": answer_text,
        "answer_type": "passage_mcq",
        "givens_json": to_json_list(extract_givens(q + " " + article)),
        "unknowns_json": to_json_list(extract_unknowns(q)),
        "method_tags_json": to_json_list(extract_method_tags(q, "comprehension")),
        "cognitive_level": detect_cognitive_level(q),
        "difficulty_score": difficulty_score,
        "difficulty_source": "mapped_from_source",
        "source_dataset": "race",
        "source_split": split_name,
    }

def map_arc_row(row, split_name, subset_name, idx):
    q = norm(row["question"])
    choices = row["choices"]
    options = [norm(x) for x in choices["text"]]
    labels = [str(x).strip() for x in choices["label"]]

    answer_key = str(row["answerKey"]).strip()
    answer_text = ""
    for lab, opt in zip(labels, options):
        if lab == answer_key:
            answer_text = opt
            break

    field, subject, topic, subtopic = detect_field_subject_topic(q)

    difficulty_score = 4.0 if subset_name == "ARC-Easy" else 7.0

    return {
        "question_id": f"arc_{subset_name}_{split_name}_{idx}",
        "question_type": "mcq",
        "field": field if field != "general" else "science",
        "subject": subject if subject != "general" else "school science",
        "topic": topic if topic != "general" else "general science",
        "subtopic": subtopic,
        "education_level": "middle school",
        "question_text": q,
        "passage_text": "",
        "options_json": to_json_list(options),
        "answer_text": answer_text,
        "answer_type": "mcq",
        "givens_json": to_json_list(extract_givens(q)),
        "unknowns_json": to_json_list(extract_unknowns(q)),
        "method_tags_json": to_json_list(extract_method_tags(q, "mcq")),
        "cognitive_level": detect_cognitive_level(q),
        "difficulty_score": difficulty_score,
        "difficulty_source": "mapped_from_source",
        "source_dataset": "arc",
        "source_split": split_name,
    }

def load_race_rows():
    rows = []
    for level_name in ["middle", "high"]:
        for split_name in ["train", "validation", "test"]:
            ds = load_dataset("race", level_name, split=split_name)
            for i, row in enumerate(tqdm(ds, desc=f"RACE {level_name} {split_name}")):
                rows.append(map_race_row(row, split_name, level_name, i))
    return rows

def load_arc_rows():
    rows = []
    for subset_name in ["ARC-Easy", "ARC-Challenge"]:
        for split_name in ["train", "validation", "test"]:
            ds = load_dataset("allenai/ai2_arc", subset_name, split=split_name)
            for i, row in enumerate(tqdm(ds, desc=f"{subset_name} {split_name}")):
                rows.append(map_arc_row(row, split_name, subset_name, i))
    return rows

def clean_df(df):
    df = df.copy()
    df["question_text"] = df["question_text"].astype(str).map(norm)
    df["passage_text"] = df["passage_text"].astype(str).map(norm)

    df = df[df["question_text"] != ""]
    df = df.drop_duplicates(subset=["question_type", "question_text", "passage_text", "source_dataset"])
    df = df[MASTER_COLS]
    return df.reset_index(drop=True)

def run():
    rows = []
    rows.extend(load_race_rows())
    rows.extend(load_arc_rows())

    df = pd.DataFrame(rows)
    df = clean_df(df)

    df.to_csv(MASTER_CSV, index=False, encoding="utf-8")
    df.head(200).to_csv(SAMPLE_CSV, index=False, encoding="utf-8")

    print("saved:", MASTER_CSV)
    print("saved sample:", SAMPLE_CSV)
    print("rows:", len(df))
    print(df["question_type"].value_counts(dropna=False))
    print(df["source_dataset"].value_counts(dropna=False))
    print(df["field"].value_counts(dropna=False).head(20))

if __name__ == "__main__":
    run()