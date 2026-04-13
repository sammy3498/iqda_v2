from src.retrieval_engine import RetrievalEngine

eng = RetrievalEngine()

query = {
    "question_id": "user_2",
    "question_type": "mcq",
    "field": "physics",
    "subject": "mechanics",
    "topic": "newtons laws",
    "subtopic": "force and motion",
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

res, qfeat = eng.retrieve(query, top_k=5)

print("query features:")
for k in ["question_type","field","topic","question_form","cognitive_level","word_count","number_count"]:
    print(k, ":", qfeat[k])

print("\ntop matches:")
print(res[["similarity","difficulty_score","field","topic","education_level","question_text"]].to_string(index=False))