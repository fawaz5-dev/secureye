# Secureye

**Human verification without the fire hydrants.**

Secureye replaces CAPTCHA with a 2-second biometric check — eye liveness on mobile, keystroke rhythm on desktop. All processing happens in the browser. No biometric data ever leaves the device. No accounts. No API keys. No database. Ever.

→ **[Live demo](https://secureye.io/verify)** · **[Docs](https://secureye.io/docs)** · **[Homepage](https://secureye.io)**

---

## File structure

```
secureye/
│
├── frontend/                   ← static site (served by Render)
│   ├── index.html              ← marketing homepage
│   ├── verify.html             ← verification engine (eye + keystroke)
│   ├── docs.html               ← developer reference
│   └── secureye.js             ← embeddable widget script
│
├── backend/                    ← stateless FastAPI app (served by Render)
│   ├── main.py                 ← two endpoints: /v1/issue + /v1/verify
│   ├── signer.py               ← HMAC-SHA256 token signing + verification
│   └── requirements.txt        ← fastapi, uvicorn, pydantic
│
├── render.yaml                 ← deploys both services from this repo
├── README.md                   ← you are here
└── WHAT_IT_IS.md               ← honest description + full flow diagram
```

Every file that should exist is listed above. If any are missing from your local clone, that's the gap to fill.

---

## Why

| | reCAPTCHA / hCaptcha | Secureye |
|---|---|---|
| Avg completion time | 15–45 seconds | < 3 seconds |
| Biometric data stored | Yes (Google servers) | Never |
| Solvable by GPT-4V | Yes | No — requires a live human body |
| Behavioral tracking | Extensive | Zero |
| Registration required | Yes | No |
| GDPR-friendly | Complex | By architecture |

Image CAPTCHAs were designed when bots were dumb and humans were patient. Neither is true anymore. GPT-4V solves any image CAPTCHA in under a second. Secureye requires a live human face or a human's natural typing rhythm — things no bot farm can fake at scale.

---

## How it works

1. **Detect** — Secureye checks for a camera. Camera present → eye liveness mode. Keyboard only → keystroke rhythm mode.
2. **Verify** — MediaPipe FaceLandmarker runs entirely in WebAssembly in the browser. The camera feed never leaves the device. Keystroke timings are analyzed locally and discarded.
3. **Prove** — A signed, single-use token is issued by the Secureye API. Valid for 60 seconds.
4. **Forget** — No profile. No history. No database entry. The token expires and nothing remains.

---

## The flow — your site → Secureye → back

```
YOUR SITE (frontend)
  1. Page loads → secureye.js mounts an iframe → secureye.io/verify
  2. User completes eye scan or types the phrase inside the iframe

SECUREYE FRONTEND (verify.html)
  3. MediaPipe runs in WebAssembly — camera feed never leaves the browser
  4. Liveness passes → POST api.secureye.io/v1/issue
     body: { mode: "eye", hostname: "yoursite.com" }

SECUREYE BACKEND (main.py — stateless)
  5. Signs a JWT with HMAC-SHA256
     payload: { mode, hostname, jti, iat, exp }
  6. Returns: { success: true, token: "..." }
     No DB write. No user record. Pure cryptographic signing.

SECUREYE FRONTEND (verify.html)
  7. Posts message to parent window: { type: "secureye:verified", token }

YOUR SITE (frontend)
  8. secureye.js catches the postMessage → fires onVerified(token)
  9. You attach the token to your form and submit to your backend

YOUR BACKEND
  10. POST api.secureye.io/v1/verify  body: { token: "..." }

SECUREYE BACKEND (main.py — stateless)
  11. Verifies HMAC signature
      Checks expiry (60s TTL)
      Checks nonce not reused (in-memory replay prevention)
      Marks nonce as used
      Returns: { success: true, mode: "eye", hostname: "yoursite.com" }

YOUR BACKEND
  12. success === true → process the form
      success === false → reject
      Token is now dead. Nothing stored about the user. Ever.
```

---

## Quickstart

### 1. Add the widget to your page

```html
<!-- in <head> -->
<script src="https://cdn.secureye.io/secureye.js" defer></script>

<!-- in your form -->
<form id="my-form" action="/submit" method="POST">
  <input type="hidden" id="secureye-token" name="secureye_token">

  <div
    class="secureye-widget"
    data-callback="onVerified"
    data-theme="dark"
  ></div>

  <button type="submit" disabled id="submit-btn">Submit</button>
</form>

<script>
  function onVerified(token) {
    document.getElementById('secureye-token').value = token;
    document.getElementById('submit-btn').disabled = false;
  }
</script>
```

### 2. Validate server-side before processing the form

**Python:**
```python
import requests

token = request.form.get("secureye_token")
r = requests.post("https://api.secureye.io/v1/verify", json={"token": token})
if not r.json().get("success"):
    abort(400, "Human verification failed")
# proceed normally
```

**Node.js:**
```js
const r = await fetch("https://api.secureye.io/v1/verify", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ token: req.body.secureye_token }),
});
const { success } = await r.json();
if (!success) return res.status(400).json({ error: "Verification failed" });
// proceed normally
```

**PHP:**
```php
$r = json_decode(file_get_contents("https://api.secureye.io/v1/verify", false,
  stream_context_create(["http" => [
    "method"  => "POST",
    "header"  => "Content-Type: application/json",
    "content" => json_encode(["token" => $_POST["secureye_token"]])
  ]])
));
if (!$r->success) { http_response_code(400); exit; }
```

**curl (for testing):**
```bash
curl -X POST https://api.secureye.io/v1/verify \
  -H "Content-Type: application/json" \
  -d '{"token": "TOKEN_FROM_CLIENT"}'
```

**Success response:**
```json
{
  "success":   true,
  "mode":      "eye",
  "hostname":  "yoursite.com",
  "issued_at": 1731496180
}
```

**Failure response:**
```json
{
  "success":     false,
  "error-codes": ["token-expired"]
}
```

---

## Widget options

| Attribute | Values | Default | Description |
|---|---|---|---|
| `data-callback` | function name | — | Called with token on success |
| `data-error-callback` | function name | — | Called on failure or denied camera |
| `data-theme` | `dark` \| `light` | `dark` | Widget color scheme |
| `data-mode` | `auto` \| `eye` \| `key` | `auto` | Force a specific mode |

---

## API reference

### `POST /v1/issue`
Called automatically by `secureye.js` after liveness passes. You don't call this directly.

| Field | Type | Description |
|---|---|---|
| `mode` | string | `"eye"` or `"key"` |
| `hostname` | string | Origin the widget is running on |

### `POST /v1/verify`
Call this from your backend to validate a token.

| Field | Type | Description |
|---|---|---|
| `token` | string | The token received from the widget callback |

### `GET /health`
Returns `{ "status": "ok", "ts": <unix timestamp> }`. Use this to check if the API is up.

---

## Error codes

| Code | Meaning |
|---|---|
| `missing-input-token` | No token in the request body |
| `invalid-input-token` | Malformed token or signature mismatch |
| `token-expired` | Token is older than 60 seconds |
| `token-already-used` | Token has already been validated (single-use) |
| `invalid-mode` | Mode was not `"eye"` or `"key"` |
| `internal-error` | Server error — retry once, then open an issue |

---

## Testing

### Keystroke mode (no camera, no backend needed)
Open `frontend/verify.html` directly in any browser. Switch to Type mode.
- **Paste** the phrase → should **reject** (zero timing variance)
- **Type normally** → should **pass**

### Full end-to-end locally

```bash
# 1. start the backend
cd backend
pip install -r requirements.txt
export SECUREYE_SIGNING_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
uvicorn main:app --reload --port 8000

# 2. update API_BASE in frontend/secureye.js to http://localhost:8000

# 3. open frontend/verify.html in your browser
#    complete a verification — you'll get a real signed token

# 4. test validation
curl -X POST http://localhost:8000/v1/verify \
  -H "Content-Type: application/json" \
  -d '{"token": "PASTE_TOKEN_HERE"}'
# → { "success": true, ... }

# 5. paste the same token again
# → { "success": false, "error-codes": ["token-already-used"] }

# 6. wait 60 seconds, try again
# → { "success": false, "error-codes": ["token-expired"] }

# 7. try a garbage token
curl -X POST http://localhost:8000/v1/verify \
  -H "Content-Type: application/json" \
  -d '{"token": "fake.garbage.token"}'
# → { "success": false, "error-codes": ["invalid-input-token"] }
```

---

## Privacy

- **No biometric storage.** Camera feed and keystroke timings processed in-browser, discarded immediately.
- **No accounts.** No registration, no API keys, no secrets to manage on your end.
- **No tracking.** No concept of a returning user. Each verification is independent.
- **No cookies.** Nothing is set in the browser.
- **No database.** Backend is a stateless signing service. Nothing to breach, subpoena, or delete.
- **GDPR / CCPA compliant by architecture** — there is no personal data at any layer of the stack.

---

## Deploying to Render

Push this repo to GitHub. Connect it on [render.com](https://render.com). `render.yaml` handles everything — it defines two services: a static site for `frontend/` and a Python web service for `backend/`.

Render auto-generates `SECUREYE_SIGNING_SECRET` from `render.yaml`. You don't set it manually.

After deploy, update `API_BASE` in `frontend/secureye.js` to your Render backend URL:
```js
const API_BASE = 'https://secureye-api.onrender.com'; // your actual URL
```

---

## Self-hosting

```bash
# frontend — any static server
cd frontend && npx serve .

# backend
cd backend
pip install -r requirements.txt
export SECUREYE_SIGNING_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
export ALLOWED_ORIGINS="https://yourdomain.com"
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Known limitations

- **The trust gap on `/v1/issue`** — a bot could call this endpoint directly without running the browser liveness check. Fix planned: server-issued challenge nonce that the browser must incorporate into the liveness result.
- **In-memory nonce store** — replay prevention resets on backend restart. The 60-second TTL keeps the risk window tiny. Replace with Redis for production at scale.
- **No CDN** — `secureye.js` is on Render's free tier. Fine for low volume.

---

## Contributing

PRs welcome. Open an issue first for anything beyond bug fixes. No build step, no bundler, no framework — plain HTML, vanilla JS, and Python.

---

## License

MIT — use it however you want.

---

*Built because clicking fire hydrants is not a security measure.*
