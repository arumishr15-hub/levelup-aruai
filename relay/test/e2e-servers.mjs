// Starts a stand-in Groq plus the real relay for browser tests; prints {"relay": url}.
import {startMockGroq} from "./mock-groq.mjs";
import {startRelay} from "../dev-server.mjs";
const mock = await startMockGroq({key: "test-key"});
const relay = await startRelay({GROQ_API_KEY: "test-key", API_BASE: mock.url, ALLOWED_ORIGINS: "*", PER_IP_PER_MINUTE: "100"});
console.log(JSON.stringify({relay: `http://127.0.0.1:${relay.address().port}`}));
