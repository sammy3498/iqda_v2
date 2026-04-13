import json
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from src.explanation_engine import ExplanationEngine


def norm(s):
    return " ".join(str(s).strip().split())


def avg(nums):
    return sum(nums) / len(nums) if nums else 0.0


def score_band(score):
    if score <= 2.5:
        return "Very easy"
    if score <= 4.0:
        return "Easy"
    if score <= 6.0:
        return "Moderate"
    if score <= 8.0:
        return "Hard"
    return "Very hard"


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


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.inner = ttk.Frame(self.canvas)
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.inner.bind("<Enter>", self._bind_mousewheel)
        self.inner.bind("<Leave>", self._unbind_mousewheel)

    def _on_inner_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.win, width=event.width)

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(self, event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event=None):
        self.canvas.unbind_all("<MouseWheel>")


class MCQBuilder:
    def __init__(self, parent):
        self.parent = parent
        self.rows = []

        ttk.Label(parent, text="Question").pack(anchor="w")
        self.question = ScrolledText(parent, height=7, wrap="word", font=("Segoe UI", 11))
        self.question.pack(fill="x", pady=(4, 10))

        tool = ttk.Frame(parent)
        tool.pack(fill="x", pady=(0, 8))

        ttk.Label(tool, text="Options", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(tool, text="＋ Add option", command=self.add_option).pack(side="left", padx=(8, 0))
        ttk.Button(tool, text="Reset options", command=self.reset_options).pack(side="left", padx=(8, 0))

        self.opt_frame = ttk.Frame(parent)
        self.opt_frame.pack(fill="x")

        self.reset_options()

    def clear(self):
        self.question.delete("1.0", "end")
        self.reset_options()

    def reset_options(self):
        for r in self.rows:
            r["frame"].destroy()
        self.rows = []
        for _ in range(4):
            self.add_option()

    def add_option(self, text=""):
        idx = len(self.rows) + 1

        fr = ttk.Frame(self.opt_frame)
        fr.pack(fill="x", pady=4)

        lbl = ttk.Label(fr, text=f"Option {idx}", width=10)
        lbl.pack(side="left")

        ent = ttk.Entry(fr)
        ent.pack(side="left", fill="x", expand=True)
        ent.insert(0, text)

        def remove():
            fr.destroy()
            self.rows = [x for x in self.rows if x["frame"] is not fr]
            self.relabel()

        ttk.Button(fr, text="Remove", command=remove).pack(side="left", padx=(8, 0))
        self.rows.append({"frame": fr, "label": lbl, "entry": ent})
        self.relabel()

    def relabel(self):
        for i, row in enumerate(self.rows, 1):
            row["label"].config(text=f"Option {i}")

    def get_data(self):
        q = self.question.get("1.0", "end").strip()
        options = [norm(r["entry"].get()) for r in self.rows if norm(r["entry"].get())]
        return q, options


class CompQuestionWidget:
    def __init__(self, parent, idx, on_remove):
        self.parent = parent
        self.idx = idx
        self.on_remove = on_remove
        self.option_rows = []

        self.frame = ttk.LabelFrame(parent, text=f"Subquestion {idx}", padding=10)
        self.frame.pack(fill="x", pady=8)

        top = ttk.Frame(self.frame)
        top.pack(fill="x")

        ttk.Label(top, text="Type").pack(side="left")
        self.qtype = tk.StringVar(value="text")
        self.type_box = ttk.Combobox(
            top,
            textvariable=self.qtype,
            values=["text", "mcq"],
            width=10,
            state="readonly"
        )
        self.type_box.pack(side="left", padx=(8, 0))
        self.type_box.bind("<<ComboboxSelected>>", self.toggle_option_area)

        ttk.Button(top, text="Remove question", command=self.remove_self).pack(side="right")

        ttk.Label(self.frame, text="Question").pack(anchor="w", pady=(8, 0))
        self.question = ScrolledText(self.frame, height=4, wrap="word", font=("Segoe UI", 11))
        self.question.pack(fill="x", pady=(4, 8))

        self.opt_tools = ttk.Frame(self.frame)
        ttk.Label(self.opt_tools, text="Options", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(self.opt_tools, text="＋ Add option", command=self.add_option).pack(side="left", padx=(8, 0))
        ttk.Button(self.opt_tools, text="Reset options", command=self.reset_options).pack(side="left", padx=(8, 0))

        self.opt_frame = ttk.Frame(self.frame)
        self.toggle_option_area()

    def remove_self(self):
        self.frame.destroy()
        self.on_remove(self)

    def toggle_option_area(self, event=None):
        mode = self.qtype.get().strip().lower()
        if mode == "mcq":
            self.opt_tools.pack(fill="x", pady=(0, 6))
            self.opt_frame.pack(fill="x")
            if not self.option_rows:
                for _ in range(4):
                    self.add_option()
        else:
            self.opt_tools.pack_forget()
            self.opt_frame.pack_forget()

    def reset_options(self):
        for row in self.option_rows:
            row["frame"].destroy()
        self.option_rows = []
        for _ in range(4):
            self.add_option()

    def add_option(self, text=""):
        idx = len(self.option_rows) + 1

        fr = ttk.Frame(self.opt_frame)
        fr.pack(fill="x", pady=3)

        lbl = ttk.Label(fr, text=f"Option {idx}", width=10)
        lbl.pack(side="left")

        ent = ttk.Entry(fr)
        ent.pack(side="left", fill="x", expand=True)
        ent.insert(0, text)

        def remove():
            fr.destroy()
            self.option_rows = [x for x in self.option_rows if x["frame"] is not fr]
            self.relabel()

        ttk.Button(fr, text="Remove", command=remove).pack(side="left", padx=(8, 0))
        self.option_rows.append({"frame": fr, "label": lbl, "entry": ent})
        self.relabel()

    def relabel(self):
        for i, row in enumerate(self.option_rows, 1):
            row["label"].config(text=f"Option {i}")

    def get_data(self):
        q = self.question.get("1.0", "end").strip()
        mode = self.qtype.get().strip().lower()
        opts = [norm(r["entry"].get()) for r in self.option_rows if norm(r["entry"].get())]
        return {
            "mode": mode,
            "question": q,
            "options": opts
        }


class IQDAV2App:
    def __init__(self, root):
        self.root = root
        self.root.title("Intelligent Question Difficulty Analyzer v2")
        self.root.geometry("1280x900")
        self.root.minsize(1120, 780)

        self.engine = ExplanationEngine()

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except:
            pass

        outer = ttk.Frame(root, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Intelligent Question Difficulty Analyzer",
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")

        ttk.Label(
            outer,
            text="Similarity-based difficulty analysis with Standard, MCQ, and Comprehension input modes.",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(4, 12))

        body = ttk.Panedwindow(outer, orient="vertical")
        body.pack(fill="both", expand=True)

        top = ttk.Frame(body)
        bottom = ttk.LabelFrame(body, text="Analysis output", padding=14)

        body.add(top, weight=3)
        body.add(bottom, weight=2)

        left = ttk.LabelFrame(top, text="Question metadata", padding=12)
        left.pack(side="left", fill="y", padx=(0, 10))

        right = ttk.Frame(top)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Field").pack(anchor="w")
        self.field_var = tk.StringVar(value="physics")
        self.field_box = ttk.Combobox(
            left,
            textvariable=self.field_var,
            values=["physics", "mathematics", "biology", "reading", "science", "general"],
            state="readonly",
            width=24
        )
        self.field_box.pack(fill="x", pady=(4, 10))

        ttk.Label(left, text="Topic").pack(anchor="w")
        self.topic_ent = ttk.Entry(left)
        self.topic_ent.pack(fill="x", pady=(4, 10))
        self.topic_ent.insert(0, "newtons laws")

        ttk.Label(left, text="Subtopic (optional)").pack(anchor="w")
        self.subtopic_ent = ttk.Entry(left)
        self.subtopic_ent.pack(fill="x", pady=(4, 10))

        # buttons moved up so they are always visible
        ttk.Button(left, text="Analyze Question", command=self.run_analysis).pack(fill="x", pady=(8, 6))
        ttk.Button(left, text="Clear Current Tab", command=self.clear_current_tab).pack(fill="x", pady=(0, 6))
        ttk.Button(left, text="Clear All", command=self.clear_all).pack(fill="x", pady=(0, 10))

        helper = (
            "How to use:\n"
            "- choose the input tab\n"
            "- enter field and topic\n"
            "- click Analyze Question\n"
            "- scroll inside each tab if needed\n"
            "- the lower panel shows score, level, and explanation"
        )
        ttk.Label(left, text=helper, justify="left").pack(anchor="w", pady=(8, 0))

        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True)

        self.std_tab = ttk.Frame(self.nb)
        self.mcq_tab = ttk.Frame(self.nb)
        self.comp_tab = ttk.Frame(self.nb)

        self.nb.add(self.std_tab, text="Standard")
        self.nb.add(self.mcq_tab, text="MCQ")
        self.nb.add(self.comp_tab, text="Comprehension")

        self.build_standard_tab()
        self.build_mcq_tab()
        self.build_comp_tab()

        score_row = ttk.Frame(bottom)
        score_row.pack(fill="x")

        self.score_var = tk.StringVar(value="-")
        self.band_var = tk.StringVar(value="-")
        self.conf_var = tk.StringVar(value="Confidence: -")
        self.meaning_var = tk.StringVar(value="Run the analyzer to see the interpretation.")
        self.summary_var = tk.StringVar(value="")
        self.field_out_var = tk.StringVar(value="Field: -")
        self.topic_out_var = tk.StringVar(value="Topic: -")
        self.subtopic_out_var = tk.StringVar(value="Subtopic: -")
        self.level_out_var = tk.StringVar(value="Likely level: -")

        ttk.Label(score_row, text="Difficulty score", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Label(score_row, textvariable=self.score_var, font=("Segoe UI", 24, "bold")).pack(side="left", padx=(10, 24))

        ttk.Label(score_row, text="Band", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Label(score_row, textvariable=self.band_var, font=("Segoe UI", 14)).pack(side="left", padx=(10, 24))

        ttk.Label(score_row, textvariable=self.conf_var, font=("Segoe UI", 11)).pack(side="left")

        self.pb = ttk.Progressbar(bottom, length=700, mode="determinate", maximum=10)
        self.pb.pack(fill="x", pady=(10, 10))

        ttk.Label(bottom, textvariable=self.meaning_var, wraplength=1120, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(bottom, textvariable=self.summary_var, wraplength=1120, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 10))

        meta = ttk.Frame(bottom)
        meta.pack(fill="x", pady=(0, 8))
        ttk.Label(meta, textvariable=self.field_out_var).pack(side="left", padx=(0, 20))
        ttk.Label(meta, textvariable=self.topic_out_var).pack(side="left", padx=(0, 20))
        ttk.Label(meta, textvariable=self.subtopic_out_var).pack(side="left", padx=(0, 20))
        ttk.Label(meta, textvariable=self.level_out_var).pack(side="left", padx=(0, 20))

        ttk.Label(bottom, text="Why the model gave this score", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.reason_box = ScrolledText(bottom, height=12, wrap="word", font=("Consolas", 10))
        self.reason_box.pack(fill="both", expand=True)
        self.reason_box.config(state="disabled")

        self.fill_demo_content()

    def build_standard_tab(self):
        sf = ScrollableFrame(self.std_tab)
        sf.pack(fill="both", expand=True)
        wrap = sf.inner

        ttk.Label(wrap, text="Question").pack(anchor="w", pady=(6, 0))
        self.std_text = ScrolledText(wrap, height=12, wrap="word", font=("Segoe UI", 11))
        self.std_text.pack(fill="both", expand=True, pady=(4, 10))

    def build_mcq_tab(self):
        sf = ScrollableFrame(self.mcq_tab)
        sf.pack(fill="both", expand=True)
        wrap = sf.inner
        self.mcq_builder = MCQBuilder(wrap)

    def build_comp_tab(self):
        sf = ScrollableFrame(self.comp_tab)
        sf.pack(fill="both", expand=True)
        wrap = sf.inner

        ttk.Label(wrap, text="Passage / context").pack(anchor="w", pady=(6, 0))
        self.comp_passage = ScrolledText(wrap, height=7, wrap="word", font=("Segoe UI", 11))
        self.comp_passage.pack(fill="x", pady=(4, 10))

        tools = ttk.Frame(wrap)
        tools.pack(fill="x")
        ttk.Label(tools, text="Subquestions", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(tools, text="＋ Add question", command=self.add_comp_question).pack(side="left", padx=(8, 0))
        ttk.Button(tools, text="Reset comprehension set", command=self.reset_comp_questions).pack(side="left", padx=(8, 0))

        self.comp_q_wrap = ttk.Frame(wrap)
        self.comp_q_wrap.pack(fill="both", expand=True, pady=(10, 0))

        self.comp_widgets = []
        self.reset_comp_questions()

    def fill_demo_content(self):
        self.std_text.insert("1.0", "Explain Newton's second law of motion with a simple example.")

        self.mcq_builder.question.insert("1.0", "What force acts on a 5 kg body accelerating at 2 m/s^2?")
        vals = ["5 N", "10 N", "15 N", "20 N"]
        for i, v in enumerate(vals):
            if i < len(self.mcq_builder.rows):
                self.mcq_builder.rows[i]["entry"].delete(0, "end")
                self.mcq_builder.rows[i]["entry"].insert(0, v)

        self.comp_passage.insert(
            "1.0",
            "Newton's laws describe how forces affect motion. The second law states that force equals mass times acceleration."
        )
        if self.comp_widgets:
            w = self.comp_widgets[0]
            w.question.insert("1.0", "What happens to force if mass stays constant and acceleration doubles?")
            w.qtype.set("text")
            w.toggle_option_area()

    def clear_current_tab(self):
        current = self.nb.tab(self.nb.select(), "text")
        if current == "Standard":
            self.std_text.delete("1.0", "end")
        elif current == "MCQ":
            self.mcq_builder.clear()
        else:
            self.comp_passage.delete("1.0", "end")
            self.reset_comp_questions()

    def clear_all(self):
        self.std_text.delete("1.0", "end")
        self.mcq_builder.clear()
        self.comp_passage.delete("1.0", "end")
        self.reset_comp_questions()

        self.score_var.set("-")
        self.band_var.set("-")
        self.conf_var.set("Confidence: -")
        self.meaning_var.set("Run the analyzer to see the interpretation.")
        self.summary_var.set("")
        self.field_out_var.set("Field: -")
        self.topic_out_var.set("Topic: -")
        self.subtopic_out_var.set("Subtopic: -")
        self.level_out_var.set("Likely level: -")
        self.pb["value"] = 0

        self.reason_box.config(state="normal")
        self.reason_box.delete("1.0", "end")
        self.reason_box.config(state="disabled")

    def reset_comp_questions(self):
        for w in self.comp_widgets:
            w.frame.destroy()
        self.comp_widgets = []
        self.add_comp_question()

    def add_comp_question(self):
        idx = len(self.comp_widgets) + 1
        w = CompQuestionWidget(self.comp_q_wrap, idx, self.remove_comp_question)
        self.comp_widgets.append(w)
        self.relabel_comp_questions()

    def remove_comp_question(self, widget):
        self.comp_widgets = [x for x in self.comp_widgets if x is not widget]
        self.relabel_comp_questions()

    def relabel_comp_questions(self):
        for i, w in enumerate(self.comp_widgets, 1):
            w.idx = i
            w.frame.config(text=f"Subquestion {i}")

    def base_meta(self):
        field = norm(self.field_var.get()).lower()
        topic = norm(self.topic_ent.get()).lower()
        subtopic = norm(self.subtopic_ent.get()).lower()
        return field, topic, subtopic

    def make_query(self, qtype, question_text, passage_text="", options=None):
        field, topic, subtopic = self.base_meta()
        return {
            "question_id": "user_input",
            "question_type": qtype,
            "field": field if field else "general",
            "subject": "",
            "topic": topic if topic else "general",
            "subtopic": subtopic,
            "education_level": "",
            "difficulty_score": 0,
            "question_text": question_text,
            "passage_text": passage_text,
            "options_json": json.dumps(options or [], ensure_ascii=False),
            "answer_text": "",
            "answer_type": "mcq" if options else ("passage_text" if qtype == "comprehension" else "text"),
            "givens_json": "[]",
            "unknowns_json": "[]",
            "method_tags_json": "[]",
            "cognitive_level": ""
        }

    def run_analysis(self):
        current = self.nb.tab(self.nb.select(), "text")
        try:
            if current == "Standard":
                self.analyze_standard()
            elif current == "MCQ":
                self.analyze_mcq()
            else:
                self.analyze_comprehension()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def analyze_standard(self):
        q = self.std_text.get("1.0", "end").strip()
        if not q:
            raise ValueError("Please enter a standard question.")
        query = self.make_query("standard", q)
        out = self.engine.analyze(query, top_k=5)
        self.render_single_output(out)

    def analyze_mcq(self):
        q, opts = self.mcq_builder.get_data()
        if not q:
            raise ValueError("Please enter an MCQ question.")
        if len(opts) < 2:
            raise ValueError("Please enter at least two options.")
        query = self.make_query("mcq", q, options=opts)
        out = self.engine.analyze(query, top_k=5)
        self.render_single_output(out)

    def analyze_comprehension(self):
        passage = self.comp_passage.get("1.0", "end").strip()
        if not passage:
            raise ValueError("Please enter the comprehension passage.")

        subqs = []
        for w in self.comp_widgets:
            data = w.get_data()
            if data["question"]:
                subqs.append(data)

        if not subqs:
            raise ValueError("Please add at least one comprehension subquestion.")

        results = []
        for item in subqs:
            opts = item["options"] if item["mode"] == "mcq" else []
            query = self.make_query("comprehension", item["question"], passage_text=passage, options=opts)
            out = self.engine.analyze(query, top_k=5)
            results.append((item, out))

        self.render_comprehension_output(results)

    def render_single_output(self, out):
        score = out["difficulty_score"]
        self.score_var.set(f"{score}/10")
        self.band_var.set(out["difficulty_band"])
        self.conf_var.set(f"Confidence: {out['confidence']}")
        self.meaning_var.set(out["score_meaning"])
        self.summary_var.set(out["summary"])
        self.field_out_var.set(f"Field: {out['predicted_field']}")
        self.topic_out_var.set(f"Topic: {out['topic']}")
        self.subtopic_out_var.set(f"Subtopic: {out['subtopic'] if out['subtopic'] else '-'}")
        self.level_out_var.set(f"Likely level: {out['predicted_level']}")
        self.pb["value"] = score

        lines = []
        for line in out["explanation_lines"]:
            lines.append(f"- {line}")

        if out["top_matches"]:
            lines.append("")
            lines.append("Top similar stored questions:")
            for i, row in enumerate(out["top_matches"], 1):
                lines.append(
                    f"{i}. sim={row['similarity']} | diff={row['difficulty_score']} | "
                    f"{row['field']} | {row['topic']} | {row['subtopic']} | {row['education_level']}"
                )
                lines.append(f"   {row['question_text']}")

        self.reason_box.config(state="normal")
        self.reason_box.delete("1.0", "end")
        self.reason_box.insert("1.0", "\n".join(lines))
        self.reason_box.config(state="disabled")

    def render_comprehension_output(self, results):
        scores = [x[1]["difficulty_score"] for x in results]
        confs = [x[1]["confidence"] for x in results]

        avg_score = round(avg(scores), 2)
        avg_conf = round(avg(confs), 3)
        band = score_band(avg_score)

        first = results[0][1]
        self.score_var.set(f"{avg_score}/10")
        self.band_var.set(band)
        self.conf_var.set(f"Confidence: {avg_conf}")
        self.meaning_var.set(band_meaning(avg_score, band))
        self.summary_var.set(f"Comprehension set analyzed across {len(results)} subquestion(s).")
        self.field_out_var.set(f"Field: {first['predicted_field']}")
        self.topic_out_var.set(f"Topic: {first['topic']}")
        self.subtopic_out_var.set("Subtopic: mixed")
        self.level_out_var.set(f"Likely level: {first['predicted_level']}")
        self.pb["value"] = avg_score

        lines = []
        lines.append(f"Average difficulty across the comprehension set: {avg_score}/10 ({band}).")
        lines.append(f"Average confidence: {avg_conf}.")
        lines.append("")

        for i, (item, out) in enumerate(results, 1):
            lines.append(f"Subquestion {i}:")
            lines.append(f"  type: {item['mode']}")
            lines.append(f"  score: {out['difficulty_score']}/10")
            lines.append(f"  band: {out['difficulty_band']}")
            lines.append(f"  topic: {out['topic']}")
            lines.append(f"  subtopic: {out['subtopic'] if out['subtopic'] else '-'}")
            lines.append(f"  confidence: {out['confidence']}")
            for line in out["explanation_lines"]:
                lines.append(f"  - {line}")
            if out["top_matches"]:
                lines.append("  top matches:")
                for j, row in enumerate(out["top_matches"][:3], 1):
                    lines.append(
                        f"    {j}. sim={row['similarity']} | diff={row['difficulty_score']} | "
                        f"{row['topic']} | {row['subtopic']} | {row['education_level']}"
                    )
                    lines.append(f"       {row['question_text']}")
            lines.append("")

        self.reason_box.config(state="normal")
        self.reason_box.delete("1.0", "end")
        self.reason_box.insert("1.0", "\n".join(lines))
        self.reason_box.config(state="disabled")


def main():
    root = tk.Tk()
    IQDAV2App(root)
    root.mainloop()


if __name__ == "__main__":
    main()