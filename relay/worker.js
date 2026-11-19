// LevelUp_AruAI relay: a free Cloudflare Worker that keeps one Groq API key secret
// and lets every learner use live AI with no account and no key.
//
// It never accepts a raw prompt. Each route takes a small context object, checks it,
// and builds the prompt itself (prompts.js), so the key can't be reused as a general chatbot.
//
// Routes:  GET /health   POST /question   POST /explain (streams text)   POST /chat (streams text)
// Settings (wrangler.toml [vars] or dashboard): MODEL, FALLBACK_MODEL, API_BASE, ALLOWED_ORIGINS,
//   PER_IP_PER_MINUTE, REASONING_EFFORT.   Secret: GROQ_API_KEY  (wrangler secret put GROQ_API_KEY)
import {questionPrompt, explainPrompt, chatMessages, cleanHistory} from "./prompts.js";

const DEFAULTS = {
  API_BASE: "https://api.groq.com/openai/v1",
  MODEL: "openai/gpt-oss-120b",
  FALLBACK_MODEL: "openai/gpt-oss-20b",
  PER_IP_PER_MINUTE: "12",
  REASONING_EFFORT: "low",
};
const MAX_BODY = 20000;
const hits = new Map(); // best-effort per-IP limiter (per Worker instance)

const cfg = (env, k) => (env && env[k] !== undefined && env[k] !== "" ? String(env[k]) : DEFAULTS[k]);

function corsHeaders(req, env) {
  const origin = req.headers.get("Origin") || "";
  const allowed = String(env.ALLOWED_ORIGINS || "*").split(",").map(s => s.trim()).filter(Boolean);
  const any = allowed.includes("*");
  return {
    ok: any || !origin || allowed.includes(origin),
    headers: {
      "Access-Control-Allow-Origin": any ? "*" : (allowed.includes(origin) ? origin : allowed[0] || ""),
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
      "Vary": "Origin",
    },
  };
}
const json = (data, status, cors) => new Response(JSON.stringify(data), {status, headers: {...cors, "Content-Type": "application/json"}});

export function tooMany(ip, perMinute, now = Date.now()) {
  const recent = (hits.get(ip) || []).filter(t => now - t < 60000);
  if (recent.length >= perMinute) { hits.set(ip, recent); return true; }
  recent.push(now); hits.set(ip, recent);
  if (hits.size > 5000) hits.clear();
  return false;
}
export function _resetLimiter() { hits.clear(); }

async function callModel(env, body) {
  const models = [cfg(env, "MODEL"), cfg(env, "FALLBACK_MODEL")].filter((m, i, a) => m && a.indexOf(m) === i);
  let last = null;
  for (const model of models) {
    const payload = {...body, model};
    const effort = cfg(env, "REASONING_EFFORT");
    if (effort && /gpt-oss/.test(model)) payload.reasoning_effort = effort;
    const res = await fetch(cfg(env, "API_BASE").replace(/\/$/, "") + "/chat/completions", {
      method: "POST",
      headers: {"Content-Type": "application/json", "Authorization": `Bearer ${env.GROQ_API_KEY}`},
      body: JSON.stringify(payload),
    });
    if (res.ok) return {res, model};
    last = res;
    // busy, retired or unknown model: try the backup model
    if (![404, 429, 503].includes(res.status) && !(res.status === 400 && /model/i.test(await res.clone().text()))) break;
  }
  return {res: last, model: null};
}

function textStream(upstream) {
  const {readable, writable} = new TransformStream();
  const writer = writable.getWriter();
  const enc = new TextEncoder(), dec = new TextDecoder();
  (async () => {
    const reader = upstream.body.getReader();
    let buf = "";
    try {
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        buf += dec.decode(value, {stream: true});
        let i;
        while ((i = buf.indexOf("\n")) >= 0) {
          const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (data === "[DONE]") continue;
          try {
            const t = JSON.parse(data).choices?.[0]?.delta?.content;   // reasoning text is never sent on
            if (t) await writer.write(enc.encode(t));
          } catch (e) { /* skip keep-alives and partial lines */ }
        }
      }
    } catch (e) { /* client went away */ }
    finally { try { await writer.close(); } catch (e) {} }
  })();
  return readable;
}

function parseQuestion(text) {
  try { return JSON.parse(text); } catch (e) {}
  const m = String(text || "").match(/\{[\s\S]*\}/);
  if (!m) return null;
  try { return JSON.parse(m[0]); } catch (e) { return null; }
}

export default {
  async fetch(req, env) {
    const {ok, headers: cors} = corsHeaders(req, env);
    if (req.method === "OPTIONS") return new Response(null, {status: ok ? 204 : 403, headers: cors});
    if (!ok) return json({error: "origin_not_allowed"}, 403, cors);

    const path = new URL(req.url).pathname.replace(/\/+$/, "") || "/";
    if (req.method === "GET" && (path === "/health" || path === "/")) {
      return json({ok: true, app: "LevelUp_AruAI relay", configured: !!env.GROQ_API_KEY, model: cfg(env, "MODEL")}, 200, cors);
    }
    if (req.method !== "POST" || !["/question", "/explain", "/chat"].includes(path)) return json({error: "not_found"}, 404, cors);
    if (!env.GROQ_API_KEY) return json({error: "relay_not_configured"}, 500, cors);
    if (Number(req.headers.get("Content-Length") || 0) > MAX_BODY) return json({error: "too_large"}, 413, cors);

    const ip = req.headers.get("CF-Connecting-IP") || "local";
    if (tooMany(ip, Number(cfg(env, "PER_IP_PER_MINUTE")))) return json({error: "rate_limited"}, 429, {...cors, "Retry-After": "30"});

    let body;
    try { const raw = await req.text(); if (raw.length > MAX_BODY) throw 0; body = JSON.parse(raw); } catch (e) { return json({error: "bad_request"}, 400, cors); }
    if (!body || typeof body !== "object") return json({error: "bad_request"}, 400, cors);

    let request;
    if (path === "/question") {
      request = {messages: [{role: "user", content: questionPrompt(body.ctx)}], response_format: {type: "json_object"}, max_tokens: 3000, temperature: 0.9};
    } else if (path === "/explain") {
      request = {messages: [{role: "user", content: explainPrompt(body.ctx)}], stream: true, max_tokens: 1200, temperature: 0.6};
    } else {
      if (!cleanHistory(body.history)) return json({error: "bad_request"}, 400, cors);
      request = {messages: chatMessages(body.ctx, body.history, true), stream: true, max_tokens: 1200, temperature: 0.6};
    }

    let up;
    try { up = await callModel(env, request); } catch (e) { return json({error: "upstream_unreachable"}, 502, cors); }
    if (!up.model) {
      const status = up.res && up.res.status === 429 ? 429 : 502;
      return json({error: status === 429 ? "rate_limited" : "upstream_error"}, status, {...cors, "Retry-After": "30"});
    }

    if (path === "/question") {
      const data = await up.res.json().catch(() => null);
      const q = parseQuestion(data?.choices?.[0]?.message?.content);
      if (!q) return json({error: "bad_model_output"}, 502, cors);
      return json({question: q, model: up.model}, 200, cors);
    }
    return new Response(textStream(up.res), {status: 200, headers: {...cors, "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store", "X-Model": up.model}});
  },
};
