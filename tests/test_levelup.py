import json

import pytest

from levelup_aruai import AgentError, Coordinator, Message, QuestionAgent, TeacherAgent, TOPICS
from levelup_aruai.__main__ import main
from levelup_aruai.lessons import LESSONS
from levelup_aruai.runner import run_snippet
from levelup_aruai.templates import TEMPLATES


# ------------------------------------------------------------------ runner
def test_runner_captures_output():
    assert run_snippet("print(1 + 1)\nprint('hi')").output == "2\nhi"


def test_runner_reports_errors_as_data():
    r = run_snippet("x = {}\nprint(x['nope'])")
    assert r.error.startswith("KeyError")


def test_runner_traces_lines_and_functions():
    r = run_snippet("def f(n):\n    return n * 2\ny = f(3)\nprint(y)", trace=True)
    lines = [s.line for s in r.steps]
    assert lines[0] == 1 and 2 in lines and lines[-1] == 4
    assert any(s.scope == "f" for s in r.steps)
    assert r.final_variables["y"] == "6"


def test_runner_truncates_long_traces():
    r = run_snippet("t = 0\nfor i in range(500):\n    t += i\nprint(t)", trace=True)
    assert r.truncated and r.output == str(sum(range(500)))


# ------------------------------------------------------------------ templates
def test_every_level_of_every_topic_exists():
    for topic in TOPICS:
        for level in (1, 2, 3):
            assert any(t.topic == topic and t.level == level for t in TEMPLATES), (topic, level)


def test_every_concept_has_a_lesson():
    assert {t.concept for t in TEMPLATES} <= set(LESSONS)


@pytest.mark.parametrize("tpl", TEMPLATES, ids=lambda t: t.key)
def test_template_answers_are_correct_and_options_valid(tpl):
    qa = QuestionAgent(seed=1)
    for _ in range(40):  # many random variants per template
        q = qa.generate(template_key=tpl.key)
        truth = run_snippet(q.code)
        assert truth.error is None, q.code
        assert q.answer == truth.output
        assert len(q.options) == 4 and len(set(q.options)) == 4
        assert q.answer in q.options
        assert set(q.misconceptions) == set(q.options) - {q.answer}
        assert q.hint and q.why


# ------------------------------------------------------------------ question agent
def test_question_agent_respects_topic_and_level():
    qa = QuestionAgent(seed=5)
    q = qa.generate(topic="loops", level=3)
    assert (q.topic, q.level) == ("loops", 3)


def test_question_agent_is_reproducible_with_seed():
    assert QuestionAgent(seed=9).generate().code == QuestionAgent(seed=9).generate().code


def test_question_agent_rejects_bad_input():
    qa = QuestionAgent()
    with pytest.raises(AgentError):
        qa.generate(topic="quantum")
    with pytest.raises(AgentError):
        qa.handle(Message("x", "question_agent", "dance"))


def test_adjust_message_clamps_level():
    qa = QuestionAgent()
    qa.handle(Message("teacher", "question_agent", "adjust", {"level": 99, "focus": "strings"}))
    assert qa.level == 3 and qa.focus == "strings"
    qa.handle(Message("teacher", "question_agent", "adjust", {"level": -4}))
    assert qa.level == 1


# ------------------------------------------------------------------ teacher agent
def _q(level=1, topic="strings"):
    return QuestionAgent(seed=2).generate(topic=topic, level=level)


def test_teacher_gives_lesson_with_question():
    q = _q()
    [msg] = TeacherAgent().handle(Message("question_agent", "teacher", "question", {"question": q}))
    assert msg.kind == "lesson" and msg.payload["lesson"]["title"]


def test_teacher_explains_wrong_answer_with_misconception():
    t, q = TeacherAgent(), _q()
    wrong = next(o for o in q.options if o != q.answer)
    fb, _ = t.assess(q, wrong)
    assert not fb["correct"] and q.misconceptions[wrong] in fb["message"]
    assert fb["walkthrough"][-1] == f"Printed: {q.answer}"
    assert fb["xp_gained"] == 0


def test_teacher_xp_and_hint_penalty():
    t = TeacherAgent()
    q1 = _q()
    fb, _ = t.assess(q1, q1.answer)
    assert fb["xp_gained"] == 15  # 10*level + 5 no-hint bonus
    q2 = _q()
    t.handle(Message("c", "teacher", "hint", {"question": q2}))
    fb, _ = t.assess(q2, q2.answer)
    assert fb["xp_gained"] == 10


def test_teacher_rejects_unknown_choice():
    with pytest.raises(AgentError):
        TeacherAgent().assess(_q(), "definitely not an option")


def test_teacher_levels_up_then_down():
    t = TeacherAgent()
    for _ in range(3):
        q = _q()
        fb, adj = t.assess(q, q.answer)
    assert fb["level_change"] == "up" and adj["level"] == 2
    for _ in range(2):
        q = _q()
        fb, adj = t.assess(q, next(o for o in q.options if o != q.answer))
    assert fb["level_change"] == "down" and adj["level"] == 1


def test_teacher_focuses_weakest_topic():
    t = TeacherAgent()
    q = _q(topic="loops")
    _, adj = t.assess(q, next(o for o in q.options if o != q.answer))
    assert adj["focus"] == "loops"


def test_rank_progression():
    t = TeacherAgent()
    assert t.rank == "Python Hatchling"
    t.xp = 460
    assert t.rank == "Function Knight"


# ------------------------------------------------------------------ connected agents
def test_full_round_trip_through_coordinator():
    game = Coordinator(seed=4)
    data = game.next_question()
    assert data["lesson"]["concept"] == data["question"].concept
    fb = game.answer(data["question"].answer)
    assert fb["correct"]
    kinds = [(m.sender, m.recipient, m.kind) for m in game.log]
    assert kinds == [
        ("coordinator", "question_agent", "request_question"),
        ("question_agent", "teacher", "question"),
        ("teacher", "coordinator", "lesson"),
        ("coordinator", "teacher", "answer"),
        ("teacher", "coordinator", "feedback"),
        ("teacher", "question_agent", "adjust"),
    ]


def test_teacher_steers_question_agent():
    game = Coordinator(seed=8)
    for _ in range(3):
        q = game.next_question(topic="lists")["question"]
        game.answer(q.answer)
    assert game.question_agent.level == 2
    assert game.next_question()["question"].level == 2


def test_weak_topic_becomes_next_question():
    game = Coordinator(seed=8)
    q = game.next_question(topic="dictionaries")["question"]
    game.answer(next(o for o in q.options if o != q.answer))
    assert game.next_question()["question"].topic == "dictionaries"


def test_coordinator_requires_question_first():
    with pytest.raises(AgentError):
        Coordinator().answer("x")


# ------------------------------------------------------------------ cli + export
def test_cli_plays_a_game():
    out = []
    answers = iter(["h", "a", "b", "q"])
    game = main(["--rounds", "3", "--seed", "1"], input_fn=lambda _: next(answers), print_fn=out.append)
    text = "\n".join(out)
    assert "Teacher:" in text and "💡" in text and "Walkthrough" in text and "Bye!" in text
    assert game.teacher.stats and sum(s.attempts for s in game.teacher.stats.values()) == 2


def test_export_bank_is_valid_json(tmp_path):
    from export_bank import build
    data = build(per_template=3)
    json.loads(json.dumps(data, ensure_ascii=False))
    assert len(data["questions"]) == 3 * len(TEMPLATES)
    for q in data["questions"]:
        assert q["answer"] in q["options"] and q["walkthrough"]


@pytest.mark.parametrize("tpl", TEMPLATES, ids=lambda t: t.key)
def test_no_junk_options(tpl):
    """Every option should be a believable answer, never padding like 'a !'."""
    qa = QuestionAgent(seed=11)
    for _ in range(300):
        q = qa.generate(template_key=tpl.key)
        assert "a guess" not in " ".join(q.misconceptions.values()), (q.code, q.options)
