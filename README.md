# Secureye

**Human verification without the fire hydrants.**

Secureye replaces CAPTCHA with a 2-second biometric check — eye liveness on mobile, keystroke rhythm on desktop. All processing happens in the browser. No biometric data ever leaves the device.

→ **[Live demo](https://secureye.io/verify)** · **[Docs](https://secureye.io/docs)** · **[Homepage](https://secureye.io)**

---

## Why

| | reCAPTCHA / hCaptcha | Secureye |
|---|---|---|
| Avg completion time | 15–45 seconds | < 3 seconds |
| Biometric data stored | Yes (Google servers) | Never |
| Solvable by GPT-4V | Yes | No — requires a live human body |
| Behavioral tracking | Extensive | Zero |
| GDPR-friendly | Complex | By architecture |

Image CAPTCHAs were designed when bots were dumb and humans were patient. Neither is true anymore. GPT-4V solves any image CAPTCHA in under a second. Secureye requires a live human face or a human's natural typing rhythm — things no bot farm can fake at scale.

---

## How it works

1. **Detect** — Secureye checks for a camera. Camera present → eye mode. Keyboard only → keystroke mode.
2. **Verify** — A lightweight ML model runs entirely in the browser via WebAssembly. The camera feed never leaves the device.
3. **Prove** — A signed, single-use token is issued. Valid for 60 seconds. Tied to your domain.
4. **Forget** — No profile. No history. No database entry. Architecturally impossible to link two sessions.

---

## Quickstart

### 1. Get a sitekey

[Register at secureye.io →](https://secureye.io/dashboard)

Free tier: **10,000 verifications/month**, no credit card.

### 2. Add the widget

```html
<!-- In your <head> -->
<script src="https://cdn.secureye.io/secureye.js" defer></script>

<!-- Where you want the widget -->
<div
  class="secureye-widget"
  data-sitekey="YOUR_SITEKEY"
  data-callback="onVerified"
></div>

<script>
  function onVerified(token) {
    // token is a single-use string, expires in 60s
    // send it to your backend for validation
    document.getElementById('my-form').submit();
  }
</script>
```

### 3. Validate server-side

Send the token from your frontend to your backend, then verify it:

```bash
curl -X POST https://api.secureye.io/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "YOUR_SECRET_KEY",
    "token": "TOKEN_FROM_CLIENT"
  }'
```

**Response:**

```json
{
  "success": true,
  "mode": "eye",
  "issued_at": "2025-11-01T14:23:01Z",
  "hostname": "yoursite.com"
}
```

If `success` is `true`, the user is verified. Reject the request if it's `false` or if the request to our API fails.

---

## Widget options

```html
<div
  class="secureye-widget"
  data-sitekey="YOUR_SITEKEY"
  data-callback="onVerified"
  data-error-callback="onError"
  data-theme="dark"
  data-mode="auto"
></div>
```

| Attribute | Values | Default | Description |
|---|---|---|---|
| `data-sitekey` | string | required | Your site's public key |
| `data-callback` | function name | — | Called with token on success |
| `data-error-callback` | function name | — | Called if verification fails |
| `data-theme` | `dark` \| `light` | `dark` | Widget color scheme |
| `data-mode` | `auto` \| `eye` \| `key` | `auto` | Force a verification mode |

---

## JavaScript API

If you need programmatic control:

```js
// Manually trigger verification
Secureye.execute('YOUR_SITEKEY', { callback: onVerified });

// Reset the widget
Secureye.reset();

// Listen for events
document.querySelector('.secureye-widget')
  .addEventListener('secureye:verified', (e) => {
    console.log(e.detail.token);
  });
```

---

## Server-side libraries

| Language | Package | Install |
|---|---|---|
| Node.js | `secureye-node` | `npm i secureye-node` |
| Python | `secureye-python` | `pip install secureye` |
| PHP | `secureye/secureye-php` | `composer require secureye/secureye-php` |
| Go | `github.com/secureye/secureye-go` | `go get github.com/secureye/secureye-go` |

**Node.js example:**

```js
import { Secureye } from 'secureye-node';

const client = new Secureye({ secret: process.env.SECUREYE_SECRET });

app.post('/submit', async (req, res) => {
  const result = await client.verify(req.body.secureye_token);
  if (!result.success) return res.status(400).json({ error: 'Verification failed' });
  // proceed with form submission
});
```

---

## Privacy

- **No biometric storage.** The camera feed and keystroke data are processed locally and immediately discarded.
- **No cross-site tracking.** Tokens are scoped to a single domain and expire in 60 seconds.
- **No user accounts.** We have no concept of a returning user. Every verification is independent.
- **No cookies.** We set nothing in the browser.
- **GDPR / CCPA compliant by architecture** — there is no personal data to request, delete, or export.

The client-side verification code is open source and auditable. You can inspect exactly what runs in your visitor's browser.

---

## Pricing

| Plan | Verifications/mo | Price |
|---|---|---|
| Free | 10,000 | $0 — forever |
| Growth | 500,000 | $29/mo |
| Enterprise | Unlimited | Contact us |

[Full pricing details →](https://secureye.io/#pricing)

---

## Self-hosting

The widget and verification UI are static files. You can serve them yourself:

```bash
git clone https://github.com/secureye/secureye
cd secureye
# serve with any static file server
npx serve .
```

Token signing requires a backend. See [self-hosting docs →](https://secureye.io/docs#self-hosting)

---

## Contributing

PRs welcome. Please open an issue first for anything beyond bug fixes.

```bash
git clone https://github.com/secureye/secureye
cd secureye
# no build step — edit the HTML/JS files directly
open index.html
```

---

## License

MIT — use it however you want.

---

*Built because clicking fire hydrants is not a security measure.*
