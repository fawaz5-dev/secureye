/**
 * secureye.js — embeddable human verification widget
 * Drop this script on any page to add Secureye verification.
 *
 * Usage:
 *   <script src="https://cdn.secureye.io/secureye.js" defer></script>
 *   <div class="secureye-widget"
 *        data-sitekey="YOUR_KEY"
 *        data-callback="onVerified">
 *   </div>
 *
 * The callback receives a single-use signed token valid for 60 seconds.
 * Validate it server-side via POST https://api.secureye.io/v1/verify
 */

(function () {
  'use strict';

  const VERIFY_ORIGIN = 'https://secureye.io';
  const WIDGET_CLASS  = 'secureye-widget';

  function init() {
    document.querySelectorAll('.' + WIDGET_CLASS).forEach(mount);
  }

  function mount(container) {
    const sitekey  = container.dataset.sitekey  || 'demo';
    const callback = container.dataset.callback || null;
    const theme    = container.dataset.theme    || 'dark';

    const iframe = document.createElement('iframe');
    iframe.src = VERIFY_ORIGIN + '/verify.html'
      + '?sitekey=' + encodeURIComponent(sitekey)
      + '&theme='   + encodeURIComponent(theme)
      + '&embedded=1';
    iframe.style.cssText = 'border:none;width:440px;max-width:100%;height:520px;border-radius:10px;';
    iframe.allow = 'camera';
    iframe.title = 'Secureye human verification';
    container.appendChild(iframe);

    window.addEventListener('message', function (e) {
      if (e.origin !== VERIFY_ORIGIN) return;
      if (!e.data || e.data.type !== 'secureye:verified') return;
      if (callback && typeof window[callback] === 'function') {
        window[callback](e.data.token);
      }
      container.dispatchEvent(new CustomEvent('secureye:verified', {
        detail: { token: e.data.token },
        bubbles: true,
      }));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
