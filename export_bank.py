"""Export a bank of agent-generated questions (with lessons + walkthroughs) for the web app."""
import json
import sys

from levelup_aruai.agents import QuestionAgent, TeacherAgent
from levelup_aruai.lessons import LESSONS
from levelup_aruai.runner import run_snippet
from levelup_aruai.templates import TEMPLATES, TOPICS


def build(per_template=8, seed=2026):
    qa, teacher = QuestionAgent(seed=seed), TeacherAgent()
    bank = []
    for tpl in TEMPLATES:
        seen = set()
        for _ in range(per_template * 3):
            q = qa.generate(template_key=tpl.key)
            if q.code in seen:
                continue
            seen.add(q.code)
            d = q.to_dict()
            d["walkthrough"] = teacher.walkthrough(q)
            run = run_snippet(q.code, trace=True)
            d["trace"] = [{"line": st.line, "scope": st.scope, "vars": st.variables} for st in run.steps]
            d["final"] = run.final_variables
            bank.append(d)
            if len(seen) == per_template:
                break
    return {"topics": TOPICS, "lessons": LESSONS, "questions": bank}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "bank.json"
    data = build()
    with open(out, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"wrote {len(data['questions'])} questions to {out}")
