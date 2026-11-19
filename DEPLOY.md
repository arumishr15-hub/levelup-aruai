# Put LevelUp_AruAI online with free AI (about 20 minutes)

When you're done, anyone can open a link and use live AI questions, explanations and chat,
with **no account and no API key**. Here's how it fits together:

- **Groq** (free) runs the AI.
- **A Cloudflare Worker** (free) keeps your Groq key secret and passes requests on.
- **GitHub Pages** (free) hosts the app.

```
learner's browser ──► GitHub Pages (the app)
        │
        └──► Cloudflare Worker "relay" (holds the key) ──► Groq (free AI)
```

You need three free accounts: **Groq**, **Cloudflare** and **GitHub**. None of them needs a credit card for this.

---

## 1. Get a free Groq key
1. Sign up at **console.groq.com**.
2. Open **API Keys** and choose **Create API Key**.
3. Copy the key, which starts with `gsk_`. Keep it private: never paste it into the app's files.

## 2. Get Cloudflare details
1. Sign up at **dash.cloudflare.com**.
2. Copy your **Account ID**. It's shown on the right side of the Workers & Pages overview.
3. Go to **My Profile → API Tokens → Create Token** and use the **"Edit Cloudflare Workers"** template.
4. Copy the token.

## 3. Put the project on GitHub
1. Create a new repository, for example `levelup-aruai`, and upload this whole folder to it.
2. In the repo, go to **Settings → Pages** and set **Source: GitHub Actions**.
3. Go to **Settings → Secrets and variables → Actions** and add three **secrets**:

   | Name | Value |
   |---|---|
   | `GROQ_API_KEY` | your `gsk_…` key |
   | `CLOUDFLARE_API_TOKEN` | the token from step 2 |
   | `CLOUDFLARE_ACCOUNT_ID` | the account ID from step 2 |

## 4. First deploy: find your relay address
1. Open the **Actions** tab. The workflow **Deploy LevelUp_AruAI** runs on every push; you can also start it with **Run workflow**.
2. When it finishes, open the **relay** job's log. Near the end you'll see an address like
   `https://levelup-aruai-relay.<your-name>.workers.dev`.
   You can also find it in Cloudflare under **Workers & Pages**.
3. Check that the relay works by opening that address plus `/health` in a browser. You should see `"configured":true`.

## 5. Connect the app to the relay
1. In GitHub, go to **Settings → Secrets and variables → Actions → Variables** and add a variable called `RELAY_URL`.
   Its value is the relay address from step 4, with no `/health` and no trailing slash.
2. Run the workflow again.
3. Your app is live at `https://<your-github-name>.github.io/<repo-name>/`. The header button should say **Live AI**.

---

## How the free key is protected
- **The key stays hidden.** It lives only in Cloudflare's secret store. The app never sees it, and the tests check this.
- **No general chatbot.** The relay won't accept raw prompts. It only builds LevelUp questions, explanations and Python-tutor chat from a small, checked set of details.
- **Only your app can use it.** The relay answers only your GitHub Pages site; the workflow sets this for you.
- **No one can hog it.** Each visitor gets at most 12 AI requests a minute (`PER_IP_PER_MINUTE` in `relay/wrangler.toml`).
- **It can't cost you money.** If the shared free allowance runs out, Groq just says "busy". The app then switches to its 161 built-in questions until the limit resets.

## How many learners can it handle?
Groq's free plan has daily and per-minute limits for each model. See **console.groq.com → Settings → Limits** for your exact numbers.

Each live question uses one request, and each explanation and each chat reply uses one more. When the main model (`openai/gpt-oss-120b`) is busy, the relay automatically switches to the backup model (`openai/gpt-oss-20b`), which has its own allowance. That's plenty for one learner or a small group. For a whole class every day, consider Groq's paid Developer tier.

## Changing the AI model or provider
Edit `[vars]` in `relay/wrangler.toml` and push:
- `MODEL` / `FALLBACK_MODEL`: any model ID from Groq's model list.
- `API_BASE`: any OpenAI-compatible service. For example, to use **Gemini's free tier** instead:
  1. Set `API_BASE` to `https://generativelanguage.googleapis.com/v1beta/openai`.
  2. Set `MODEL` to a current Gemini Flash model ID.
  3. Put the Gemini key in the `GROQ_API_KEY` secret.

## Running it on your own computer
```
GROQ_API_KEY=gsk_... npm run dev:relay        # relay on http://127.0.0.1:8787
cd web && python -m http.server 8000          # then open http://localhost:8000
```
For local testing, set `<meta name="levelup-relay" content="http://127.0.0.1:8787">` in `web/index.html`. Don't commit that change: the deploy workflow fills in the real address.
