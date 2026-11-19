// Prompts for the two agents, built by the relay Worker from a small, checked context.
// The relay builds every prompt itself from this small, checked context, so the
// hidden API key can only ever be used for LevelUp questions, explanations and chat.

const LEVEL_NAMES = {
  1: "beginner: one idea, 2 to 5 lines",
  2: "improver: combine two ideas, 4 to 8 lines",
  3: "challenger: trickier logic such as nested loops, functions or comprehensions, 6 to 12 lines",
};

const str = (v, max) => String(v ?? "").slice(0, max);
const strList = (v, n, max) => (Array.isArray(v) ? v : []).slice(-n).map(x => str(x, max));
const level = v => Math.max(1, Math.min(3, parseInt(v, 10) || 1));
const topic = v => str(v, 40).replace(/\s+/g, " ").replace(/[^\w \-+.#()'/]/g, "").trim() || "python basics";

export function cleanQuestionCtx(c = {}) {
  return {
    topic: topic(c.topic), level: level(c.level), accuracy: str(c.accuracy, 300),
    mistakes: strList(c.mistakes, 4, 120), concepts: strList(c.concepts, 6, 40),
  };
}
export function cleanExplainCtx(c = {}) {
  return {
    code: str(c.code, 1500), options: strList(c.options, 4, 200), choice: str(c.choice, 200),
    answer: str(c.answer, 200), ok: !!c.ok, trace: str(c.trace, 3000),
  };
}
export function cleanChatCtx(c = {}) {
  const q = c.question && typeof c.question === "object" ? {
    topic: topic(c.question.topic), level: level(c.question.level),
    code: str(c.question.code, 1500), options: strList(c.question.options, 4, 200),
  } : null;
  const a = c.answered && typeof c.answered === "object" ? {ok: !!c.answered.ok, answer: str(c.answered.answer, 200)} : null;
  return {level: level(c.level), question: q, answered: a};
}
export function cleanHistory(h) {
  let msgs = (Array.isArray(h) ? h : []).slice(-10)
    .filter(m => m && (m.role === "user" || m.role === "assistant"))
    .map(m => ({role: m.role, content: str(m.content, 600)}));
  while (msgs.length && msgs[0].role !== "user") msgs = msgs.slice(1);
  if (!msgs.length || msgs[msgs.length - 1].role !== "user") return null;
  return msgs;
}

export const QUESTION_SCHEMA = `{"concept": "2-4 word name of the idea tested",
 "code": "the Python program, lines separated by \\n",
 "options": ["4 different strings, each exactly as Python would print it"],
 "answer": "the one correct option, copied exactly",
 "misconceptions": {"<each wrong option>": "the mistaken belief behind it, as an -ing phrase, e.g. 'thinking range includes its end'"},
 "hint": "one sentence that nudges without giving the answer",
 "why": "one sentence explaining the correct answer",
 "lesson": {"title": "short friendly title", "explain": "2 sentences, may use backticks for code", "example": "2-4 lines of Python", "tip": "one short memorable tip"}}`;

export function questionPrompt(ctx) {
  const c = cleanQuestionCtx(ctx);
  return `You are the Question Agent in LevelUp_AruAI, a cheerful Python practice app for a young learner.
Write ONE new multiple-choice question of the form "What does this code print?".

Topic: ${c.topic}
Level: ${c.level} of 3 (${LEVEL_NAMES[c.level]})
Learner accuracy so far: ${c.accuracy || "none yet"}
Their recent mistakes (target one of these if it fits the topic): ${c.mistakes.join("; ") || "none yet"}
Concepts already asked recently (pick a different angle): ${c.concepts.join(", ") || "none"}

Rules for the code:
- Plain Python 3, fully deterministic: no input(), no randomness, no files or network, no imports except math.
- It must run without errors and print 1 to 3 short lines.
- 2 to 12 lines. Friendly, fun names (sakura, Aru, kittens, stars, cupcakes, rockets...).
Rules for the options:
- Exactly 4 different strings, each written exactly as Python prints it (use \\n between printed lines).
- One is correct; each of the other 3 comes from a real beginner misconception.

Reply with only a JSON object in this shape:
${QUESTION_SCHEMA}`;
}

export function explainPrompt(ctx) {
  const c = cleanExplainCtx(ctx);
  return `You are the Teacher Agent in LevelUp_AruAI, a warm, encouraging Python tutor for a young learner.
Code:
${c.code}

Question: what does it print? Options: ${c.options.map(o => JSON.stringify(o)).join(", ")}
The learner chose ${JSON.stringify(c.choice)}. The correct answer, verified by running Python, is ${JSON.stringify(c.answer)}.
Trace (variables just before each line runs):
${c.trace || "(not available)"}

${c.ok ? "They got it right: celebrate briefly, then reinforce the key idea in a fresh way they might not have thought of."
       : "They got it wrong: kindly name the likely misunderstanding, then point to the exact line that decides the answer and why."}
Write 2 to 4 short sentences of plain text. Wrap code in backticks. No headings, no lists, no greeting.`;
}

export function chatSystem(ctx) {
  const c = cleanChatCtx(ctx);
  const q = c.question;
  const about = q
    ? `The question on screen (${q.topic}, level ${q.level}):\n${q.code}\nOptions: ${q.options.map(o => JSON.stringify(o)).join(", ")}\n` +
      (c.answered ? `The learner has answered (${c.answered.ok ? "correctly" : "incorrectly"}); the correct answer is ${JSON.stringify(c.answered.answer)}.`
                  : "The learner has NOT answered yet: never reveal or rule out options; give a gentle nudge instead.")
    : "No question is on screen yet.";
  return `You are the Teacher Agent in LevelUp_AruAI, a warm, encouraging Python tutor for a young learner at level ${c.level} of 3. Answer in under 120 words of plain text; short code examples are fine (backticks or indented lines). Stay on Python and learning; kindly steer anything else back.\n\n${about}`;
}

// systemRole=true for OpenAI-style APIs (Groq); false folds it into the first user turn, for APIs without system messages.
export function chatMessages(ctx, history, systemRole) {
  const msgs = cleanHistory(history);
  if (!msgs) return null;
  const sys = chatSystem(ctx);
  if (systemRole) return [{role: "system", content: sys}, ...msgs];
  return msgs.map((m, i) => i === 0 ? {role: "user", content: `${sys}\n\nLearner says: ${m.content}`} : m);
}
