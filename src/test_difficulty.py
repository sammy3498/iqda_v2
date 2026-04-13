from src.difficulty_engine import DifficultyEngine

eng = DifficultyEngine()

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

print("final score:", out["difficulty_score"])
print("band:", out["difficulty_band"])
print("retrieval anchor:", out["retrieval_score"])
print("intrinsic score:", out["intrinsic_score"])
print("blend lambda:", out["blend_lambda"])
print("predicted field:", out["predicted_field"])
print("predicted level:", out["predicted_level"])

print("\nquery subtopic:", out["query_features"]["subtopic"])

print("\ntop matches:")
print(
    out["top_matches"][[
        "similarity",
        "difficulty_score",
        "field",
        "topic",
        "subtopic",
        "education_level",
        "question_text"
    ]].to_string(index=False)
)