# What Secureye Is Right Now

## The honest one-liner

Secureye is an open source, drop-in human verification widget that runs entirely in the browser — no accounts, no API keys, no biometric storage. It's a working alternative to reCAPTCHA for developers who want something faster and more private.

---

## What actually works today

### Eye mode (camera)
Real MediaPipe FaceLandmarker model running in WebAssembly directly in the browser. It detects:
- Live face presence across frames (not a static photo)
- Natural blink detection via Eye Aspect Ratio
- Head motion (defeats freeze-frame replay)
- A randomized challenge on each attempt — blink twice, look left, look right, or nod — so recorded video replays don't work

The camera feed is processed frame by frame in memory and discarded immediately. Nothing is buffered, nothing is uploaded, nothing leaves the browser.

### Keystroke mode (keyboard fallback)
When no camera is available, the user types a randomly selected short phrase. The widget measures:
- Dwell time (how long each key is held)
- Flight time (gap between keys)
- Rhythm variance (humans are organic, bots are too consistent or too fast)

Paste the phrase or autofill it and it rejects. Type it naturally and it passes.

### Token issuance
After either check passes, the widget calls the Secureye backend which issues a signed, single-use JWT. The token contains: mode, hostname, timestamp, and a unique nonce. It expires in 60 seconds. Once validated, it's marked used — can't be reused.

---

## What doesn't exist yet

- No sitekey/account system (intentional — we removed it by design)
- No usage dashboard
- No official npm/pip packages (a single fetch() call is all you need anyway)
- No production CDN yet (currently Render's free static hosting)

---

## The flow — from a developer's site to Secureye and back

Here's exactly what happens when a user hits a form protected by Secureye:

```
┌─────────────────────────────────────────────────────────────┐
│                      DEVELOPER'S SITE                        │
│                                                             │
│  1. Page loads. secureye.js mounts an iframe pointing       │
│     to secureye.io/verify                                   │
│                                                             │
│  2. User interacts with the Secureye widget inside          │
│     the iframe (eye scan or typing)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   SECUREYE FRONTEND                          │
│                   (verify.html)                             │
│                                                             │
│  3. MediaPipe runs entirely in the browser.                 │
│     Camera feed never leaves this iframe.                   │
│     Keystroke timings analyzed in JS memory.                │
│                                                             │
│  4. Liveness check passes. Widget calls:                    │
│     POST api.secureye.io/v1/issue                           │
│     body: { mode: "eye", hostname: "yoursite.com" }         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   SECUREYE BACKEND                           │
│                   (FastAPI, stateless)                      │
│                                                             │
│  5. Backend receives mode + hostname.                       │
│     Signs a JWT with HMAC-SHA256.                           │
│     Token payload: { mode, hostname, jti, iat, exp }        │
│     Returns: { success: true, token: "sey.xxx.yyy.zzz" }   │
│                                                             │
│     No database write. No user record. Pure signing.        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   SECUREYE FRONTEND                          │
│                   (verify.html)                             │
│                                                             │
│  6. Widget receives the signed token.                       │
│     Fires postMessage to parent window:                     │
│     { type: "secureye:verified", token: "sey.xxx..." }      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DEVELOPER'S SITE                        │
│                                                             │
│  7. secureye.js catches the postMessage.                    │
│     Fires the developer's callback: onVerified(token)       │
│                                                             │
│  8. Developer attaches the token to their form and          │
│     submits. Token travels to their own backend.            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   DEVELOPER'S BACKEND                        │
│                                                             │
│  9. Backend receives form + token.                          │
│     POSTs token to api.secureye.io/v1/verify                │
│     body: { token: "sey.xxx.yyy.zzz" }                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   SECUREYE BACKEND                           │
│                                                             │
│  10. Verifies HMAC signature.                               │
│      Checks token hasn't expired (60s TTL).                 │
│      Checks nonce hasn't been used (replay prevention).     │
│      Marks nonce as used.                                   │
│      Returns: { success: true, mode: "eye",                 │
│                hostname: "yoursite.com", issued_at: ... }   │
│                                                             │
│      No database read. In-memory nonce check only.          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   DEVELOPER'S BACKEND                        │
│                                                             │
│  11. success === true → process the form normally.          │
│      success === false → reject the request.                │
│                                                             │
│      Done. The token is now dead. Nothing was stored        │
│      anywhere about the user who just verified.             │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration — the actual code

### Frontend (any HTML page)

```html
<!-- 1. Load the widget script -->
<script src="https://cdn.secureye.io/secureye.js" defer></script>

<!-- 2. Place the widget in your form -->
<form id="my-form" action="/submit" method="POST">
  <input type="hidden" id="secureye-token" name="secureye_token">

  <div
    class="secureye-widget"
    data-callback="onVerified"
    data-theme="dark"
  ></div>

  <button type="submit" id="submit-btn" disabled>Submit</button>
</form>

<script>
  function onVerified(token) {
    document.getElementById('secureye-token').value = token;
    document.getElementById('submit-btn').disabled = false;
  }
</script>
```

### Backend validation

**Python (Flask/FastAPI/Django):**
```python
import requests

token = request.form.get("secureye_token")
r = requests.post("https://api.secureye.io/v1/verify", json={"token": token})

if not r.json().get("success"):
    abort(400, "Human verification failed")

# user is verified — process the form
```

**Node.js (Express):**
```js
const token = req.body.secureye_token;
const r = await fetch("https://api.secureye.io/v1/verify", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ token }),
});
const { success } = await r.json();
if (!success) return res.status(400).send("Verification failed");
// process the form
```

**PHP:**
```php
$token = $_POST["secureye_token"];
$r = json_decode(file_get_contents("https://api.secureye.io/v1/verify", false,
  stream_context_create(["http" => [
    "method"  => "POST",
    "header"  => "Content-Type: application/json",
    "content" => json_encode(["token" => $token])
  ]])
));
if (!$r->success) { http_response_code(400); exit; }
```

---

## What the token looks like

```
sey.eyJhbGciOiJIUzI1NiIsInR5cCI6IlNFWSJ9.eyJtb2RlIjoiZXllIiwiaG9zdG5hbWUiOiJ5b3Vyc2l0ZS5jb20iLCJqdGkiOiI0ZjJhYjNjNC1kNWU2LTQ3ZjgtODlhMC1iMWMyZDNlNGY1ZzYiLCJpYXQiOjE3MzE0OTYxODAsImV4cCI6MTczMTQ5NjI0MH0.xK9mP2qR7nS4vT8wU1yV3zA5bB6cC7dD8eE9fF0g
```

Three parts separated by dots: header · payload · HMAC-SHA256 signature. Decode the payload and you get:

```json
{
  "mode":     "eye",
  "hostname": "yoursite.com",
  "jti":      "4f2ab3c4-d5e6-47f8-89a0-b1c2d3e4f5g6",
  "iat":      1731496180,
  "exp":      1731496240
}
```

No user data. No biometrics. No identity. Just a proof that someone with eyes or fingers was on your site 30 seconds ago.

---

## Known limitations right now

**The trust gap on /v1/issue.** The issue endpoint currently trusts that the client ran liveness detection. A sophisticated attacker could call `/v1/issue` directly without going through `verify.html`. This is the next thing to fix — a server-issued challenge nonce that the client must incorporate into the liveness result, making it impossible to skip the browser step.

**In-memory nonce store.** Replay prevention lives in the backend process's memory. If the backend restarts, old nonces are forgotten — meaning a token from before the restart could technically be replayed. TTL of 60 seconds makes this window very small. For production, replace with Redis.

**No CDN.** `secureye.js` is served from Render's free tier. Fine for low volume, not for scale.

These are honest engineering tradeoffs for a first version, not fundamental flaws.

---

## Self-hosting

Clone the repo. No build step.

```bash
git clone https://github.com/secureye/secureye
cd secureye/backend
pip install -r requirements.txt
export SECUREYE_SIGNING_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
uvicorn main:app --reload
```

Serve `frontend/` with any static server. Point `API_BASE` in `secureye.js` at your backend. Done.
