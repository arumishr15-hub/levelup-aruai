"""The two agents of LevelUp_AruAI and the messages they exchange.

QuestionAgent  - writes Python questions and checks the answer key by running the code.
TeacherAgent   - teaches a mini-lesson with each question, gives hints, explains
                 answers step by step, and tells the QuestionAgent what to ask next.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import Any

from .lessons import LESSONS, MISSING_LESSON
from .runner import run_snippet
from .templates import TEMPLATES, TOPICS, Template

MIN_LEVEL, MAX_LEVEL = 1, 3


@dataclass
class Message:
    sender: str
    recipient: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Question:
    id: str
    topic: str
    level: int
    concept: str
    template: str
    code: str
    prompt: str
    options: list[str]
    answer: str
    misconceptions: dict[str, str]  # wrong option -> misconception behind it
    hint: str
    why: str

    def to_dict(self) -> dict:
        return asdict(self)


class AgentError(Exception):
    pass


# =============================================================== Question Agent
class QuestionAgent:
    name = "question_agent"

    def __init__(self, seed: int | None = None, n_options: int = 4):
        self.rng = random.Random(seed)
        self.n_options = n_options
        self.level = MIN_LEVEL
        self.focus: str | None = None  # topic the Teacher wants practised
        self._count = 0

    # -- message handling
    def handle(self, msg: Message) -> list[Message]:
        if msg.kind == "request_question":
            topic = msg.payload.get("topic") or self.focus
            level = msg.payload.get("level") or self.level
            q = self.generate(topic=topic, level=level)
            return [Message(self.name, "teacher", "question", {"question": q})]
        if msg.kind == "adjust":
            self.level = max(MIN_LEVEL, min(MAX_LEVEL, int(msg.payload.get("level", self.level))))
            self.focus = msg.payload.get("focus")
            return []
        raise AgentError(f"QuestionAgent can't handle '{msg.kind}'")

    # -- generation
    def _pick_template(self, topic: str | None, level: int) -> Template:
        if topic is not None and topic not in TOPICS:
            raise AgentError(f"Unknown topic '{topic}'. Choose from: {', '.join(TOPICS)}")
        pool = [t for t in TEMPLATES if t.level == level and (topic is None or t.topic == topic)]
        if not pool:
            raise AgentError(f"No template for topic={topic!r} level={level}")
        return self.rng.choice(pool)

    def generate(self, topic: str | None = None, level: int = 1, template_key: str | None = None) -> Question:
        if template_key:
            matches = [t for t in TEMPLATES if t.key == template_key]
            if not matches:
                raise AgentError(f"Unknown template '{template_key}'")
            tpl = matches[0]
        else:
            tpl = self._pick_template(topic, level)
        spec = tpl.build(self.rng)
        result = run_snippet(spec["code"])
        if result.error:
            # A crash is a valid answer ("What happens?"), show the error type only
            answer = result.error.split(":")[0]
        else:
            answer = result.output

        misconceptions: dict[str, str] = {}
        for value, why_wrong in spec["wrong"]:
            value = str(value).rstrip()
            if value != answer and value not in misconceptions:
                misconceptions[value] = why_wrong
        options = [answer] + list(misconceptions)[: self.n_options - 1]
        step = 1
        while len(options) < self.n_options:  # distractors collided with the answer
            if answer.lstrip("-").isdigit():
                extra, why_wrong = str(int(answer) + (step if step % 2 else -step)), "an off-by-one slip in the counting"
            else:
                extra, why_wrong = answer + "!" * step, "a guess - trace the code line by line"
            if extra not in options:
                options.append(extra)
                misconceptions[extra] = why_wrong
            step += 1
        self.rng.shuffle(options)

        self._count += 1
        return Question(
            id=f"q{self._count}-{tpl.key}",
            topic=tpl.topic,
            level=tpl.level,
            concept=tpl.concept,
            template=tpl.key,
            code=spec["code"],
            prompt="What does this code print?",
            options=options,
            answer=answer,
            misconceptions={o: misconceptions[o] for o in options if o != answer},
            hint=spec["hint"],
            why=spec["why"],
        )


# =============================================================== Teacher Agent
@dataclass
class TopicStats:
    attempts: int = 0
    correct: int = 0
    streak: int = 0
    misses_in_row: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.attempts if self.attempts else 0.0


RANKS = [(0, "Python Hatchling"), (100, "Code Explorer"), (250, "Loop Ranger"),
         (450, "Function Knight"), (700, "Data Wizard"), (1000, "Python Master")]


class TeacherAgent:
    name = "teacher"
    LEVEL_UP_STREAK = 3
    LEVEL_DOWN_MISSES = 2

    def __init__(self):
        self.level = MIN_LEVEL
        self.xp = 0
        self.stats: dict[str, TopicStats] = {t: TopicStats() for t in TOPICS}
        self.hints_used: set[str] = set()

    # -- message handling
    def handle(self, msg: Message) -> list[Message]:
        if msg.kind == "question":
            q: Question = msg.payload["question"]
            return [Message(self.name, "coordinator", "lesson", {"question": q, "lesson": self.lesson_for(q)})]
        if msg.kind == "answer":
            feedback, adjust = self.assess(msg.payload["question"], msg.payload["choice"])
            out = [Message(self.name, "coordinator", "feedback", feedback)]
            if adjust:
                out.append(Message(self.name, "question_agent", "adjust", adjust))
            return out
        if msg.kind == "hint":
            q = msg.payload["question"]
            self.hints_used.add(q.id)
            return [Message(self.name, "coordinator", "hint", {"hint": q.hint})]
        raise AgentError(f"TeacherAgent can't handle '{msg.kind}'")

    # -- teaching
    def lesson_for(self, q: Question) -> dict:
        lesson = LESSONS.get(q.concept, MISSING_LESSON)
        return {"concept": q.concept, **lesson}

    def walkthrough(self, q: Question) -> list[str]:
        run = run_snippet(q.code, trace=True)
        steps = []
        for s in run.steps:
            vars_txt = ", ".join(f"{k} = {v}" for k, v in s.variables.items()) or "nothing yet"
            where = "" if s.scope == "main" else f" (inside {s.scope})"
            steps.append(f"Line {s.line}{where}: `{s.source}`  ·  known: {vars_txt}")
        if run.truncated:
            steps.append("…and it keeps going the same way.")
        final = ", ".join(f"{k} = {v}" for k, v in run.final_variables.items())
        if final:
            steps.append(f"At the end: {final}")
        steps.append(f"Printed: {run.output or run.error}")
        return steps

    def assess(self, q: Question, choice: str) -> tuple[dict, dict | None]:
        if choice not in q.options:
            raise AgentError(f"'{choice}' is not one of the options")
        correct = choice == q.answer
        st = self.stats[q.topic]
        st.attempts += 1
        gained = 0
        if correct:
            st.correct += 1
            st.streak += 1
            st.misses_in_row = 0
            gained = 10 * q.level + (0 if q.id in self.hints_used else 5) + (5 if st.streak >= 3 else 0)
            self.xp += gained
            message = f"Correct! {q.why}"
        else:
            st.streak = 0
            st.misses_in_row += 1
            reason = q.misconceptions.get(choice, "a small slip")
            message = (f"Not quite. Picking '{choice}' usually comes from {reason}. "
                       f"The answer is '{q.answer}': {q.why}")

        adjust = self._plan_next(q, st)
        feedback = {
            "correct": correct,
            "answer": q.answer,
            "message": message,
            "walkthrough": self.walkthrough(q),
            "xp_gained": gained,
            "xp": self.xp,
            "rank": self.rank,
            "level": self.level,
            "level_change": adjust.pop("_change") if adjust else None,
        }
        return feedback, adjust

    def _plan_next(self, q: Question, st: TopicStats) -> dict | None:
        change = None
        if st.streak >= self.LEVEL_UP_STREAK and self.level < MAX_LEVEL:
            self.level += 1
            st.streak = 0
            change = "up"
        elif st.misses_in_row >= self.LEVEL_DOWN_MISSES and self.level > MIN_LEVEL:
            self.level -= 1
            st.misses_in_row = 0
            change = "down"
        focus = self.weakest_topic()
        return {"level": self.level, "focus": focus, "_change": change}

    def weakest_topic(self) -> str | None:
        tried = {t: s for t, s in self.stats.items() if s.attempts}
        if not tried:
            return None
        topic, s = min(tried.items(), key=lambda kv: (kv[1].accuracy, -kv[1].attempts))
        return topic if s.accuracy < 0.6 else None

    @property
    def rank(self) -> str:
        return [name for need, name in RANKS if self.xp >= need][-1]


# =============================================================== Coordinator
class Coordinator:
    """Routes messages between the agents and keeps a transcript."""

    name = "coordinator"

    def __init__(self, seed: int | None = None):
        self.question_agent = QuestionAgent(seed=seed)
        self.teacher = TeacherAgent()
        self.agents = {a.name: a for a in (self.question_agent, self.teacher)}
        self.log: list[Message] = []
        self.current: Question | None = None

    def _dispatch(self, msg: Message) -> list[Message]:
        """Deliver ``msg`` and keep routing until replies come back to the coordinator."""
        inbox, results = [msg], []
        while inbox:
            m = inbox.pop(0)
            self.log.append(m)
            if m.recipient == self.name:
                results.append(m)
                continue
            if m.recipient not in self.agents:
                raise AgentError(f"No agent called '{m.recipient}'")
            inbox.extend(self.agents[m.recipient].handle(m))
        return results

    def next_question(self, topic: str | None = None) -> dict:
        req = Message(self.name, "question_agent", "request_question", {"topic": topic})
        [reply] = self._dispatch(req)
        self.current = reply.payload["question"]
        return reply.payload

    def hint(self) -> str:
        self._require_question()
        [reply] = self._dispatch(Message(self.name, "teacher", "hint", {"question": self.current}))
        return reply.payload["hint"]

    def answer(self, choice: str) -> dict:
        self._require_question()
        [reply] = self._dispatch(Message(self.name, "teacher", "answer",
                                         {"question": self.current, "choice": choice}))
        self.current = None
        return reply.payload

    def _require_question(self):
        if self.current is None:
            raise AgentError("Ask for a question first")
