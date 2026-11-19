// Run the relay locally:  GROQ_API_KEY=... node relay/dev-server.mjs  (PORT defaults to 8787)
// Every setting from wrangler.toml can be given as an environment variable here.
import http from "node:http";
import worker from "./worker.js";

export function startRelay(env, port = 0) {
  const server = http.createServer(async (req, res) => {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = Buffer.concat(chunks);
    const headers = new Headers();
    for (const [k, v] of Object.entries(req.headers)) if (typeof v === "string") headers.set(k, v);
    const request = new Request(`http://${req.headers.host}${req.url}`, {method: req.method, headers, body: ["GET", "HEAD"].includes(req.method) ? undefined : body});
    const out = await worker.fetch(request, env);
    res.writeHead(out.status, Object.fromEntries(out.headers));
    if (!out.body) return res.end();
    const reader = out.body.getReader();
    for (;;) { const {done, value} = await reader.read(); if (done) break; res.write(value); }
    res.end();
  });
  return new Promise(r => server.listen(port, "127.0.0.1", () => r(server)));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const env = {...process.env};
  const server = await startRelay(env, Number(process.env.PORT || 8787));
  console.log(`LevelUp relay on http://127.0.0.1:${server.address().port}  (key ${env.GROQ_API_KEY ? "set" : "MISSING"})`);
}
