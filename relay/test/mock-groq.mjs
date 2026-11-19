// A stand-in for Groq's OpenAI-compatible API, for tests. Records every request.
import http from "node:http";

export const GOOD_QUESTION = {
  concept: "string repetition", code: 'flower = "ka"\nprint(flower * 3)',
  options: ["kakaka", "ka3", "ka ka ka", "kaka"], answer: "ka3",            // deliberately wrong key
  misconceptions: {"kakaka": "x", "ka ka ka": "thinking * adds spaces", "kaka": "thinking * 3 adds two copies"},
  hint: "What does * do to a string?", why: "Strings repeat with *.",
  lesson: {title: "Repeating strings", explain: "`*` repeats a string.", example: '"ha" * 2  # "haha"', tip: "Text times number = copies."},
};

export function startMockGroq({busy = [], key = "test-key"} = {}) {
  const calls = [];
  const server = http.createServer(async (req, res) => {
    let raw = ""; for await (const c of req) raw += c;
    const body = raw ? JSON.parse(raw) : {};
    calls.push({path: req.url, auth: req.headers.authorization, body});
    if (req.headers.authorization !== `Bearer ${key}`) { res.writeHead(401); return res.end("{}"); }
    if (busy.includes(body.model)) { res.writeHead(429, {"Content-Type": "application/json"}); return res.end('{"error":{"message":"rate limit"}}'); }
    if (body.stream) {
      res.writeHead(200, {"Content-Type": "text/event-stream"});
      const isChat = body.messages[0].role === "system";
      const words = (isChat ? "Lists start at index 0 because an index counts steps from the start."
                            : "Nice thinking! On line 2, `flower * 3` repeats the text, so it prints kakaka.").split(" ");
      res.write(`data: ${JSON.stringify({choices: [{delta: {reasoning: "secret thoughts"}}]})}\n\n`);
      for (const w of words) { res.write(`data: ${JSON.stringify({choices: [{delta: {content: w + " "}}]})}\n\n`); await new Promise(r => setTimeout(r, 3)); }
      res.write("data: [DONE]\n\n"); return res.end();
    }
    res.writeHead(200, {"Content-Type": "application/json"});
    res.end(JSON.stringify({choices: [{message: {content: JSON.stringify(GOOD_QUESTION)}}]}));
  });
  return new Promise(r => server.listen(0, "127.0.0.1", () => r({server, calls, url: `http://127.0.0.1:${server.address().port}`})));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const m = await startMockGroq({busy: (process.env.BUSY || "").split(",")});
  console.log(m.url);
}
