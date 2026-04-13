from src.explanation_engine import ExplanationEngine

eng = ExplanationEngine()

query = {
    "question_id": "user_2",
    "question_type": "mcq",
    "field": "physics",
    "subject": "mechanics",
    "topic": "newtons laws",
    "subtopic": "",
    "education_level": "",
    "difficulty_score": 0,
    "question_text": "What force acts on a 5 kg body accelerating at 2 m/s^2?",
    "passage_text": "",
    "options_json": '["5 N","10 N","15 N","20 N"]',
    "answer_text": "",
    "answer_type": "mcq",
    "givens_json": '["mass","acceleration","numeric_values"]',
    "unknowns_json": '["force"]',
    "method_tags_json": '["formula_application","option_elimination"]',
    "cognitive_level": "apply"
}

out = eng.analyze(query, top_k=5)

print("summary:", out["summary"])
print("score:", out["difficulty_score"])
print("band:", out["difficulty_band"])
print("meaning:", out["score_meaning"])
print("field:", out["predicted_field"])
print("level:", out["predicted_level"])
print("topic:", out["topic"])
print("subtopic:", out["subtopic"])
print("confidence:", out["confidence"])

print("\nexplanation:")
for line in out["explanation_lines"]:
    print("-", line)

print("\ntop matches:")
for i, row in enumerate(out["top_matches"], 1):
    print(f"{i}. sim={row['similarity']} diff={row['difficulty_score']} topic={row['topic']} subtopic={row['subtopic']}")
    print("   ", row["question_text"])