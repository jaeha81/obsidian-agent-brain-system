/* checklist-crypto.js — 공개 미러(암호문)를 브라우저에서 푼다.
 *
 * 저장소가 public이라 docs/data/user_checklist.json은 누구나 받을 수 있다.
 * 그래서 파일은 AES-256-GCM 암호문으로만 게시하고, 여기서 비밀번호로 푼다.
 * 규격은 scripts/checklist_crypto.py와 같다 (PBKDF2-HMAC-SHA256 → AES-GCM).
 *
 * 비밀번호는 sessionStorage에만 둔다 — 탭을 닫으면 사라진다. 어디로도 전송하지 않는다.
 *
 * 사용: const data = await loadChecklistJson('./data/user_checklist.json');
 */
(function (global) {
  'use strict';

  var PW_KEY = 'bucky_cl_pw';

  function b64ToBytes(s) {
    var bin = atob(s);
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  async function deriveKey(password, salt, iterations) {
    var base = await crypto.subtle.importKey(
      'raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveKey']
    );
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: salt, iterations: iterations, hash: 'SHA-256' },
      base,
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt']
    );
  }

  async function decryptEnvelope(env, password) {
    var key = await deriveKey(password, b64ToBytes(env.salt), env.iter || 200000);
    var plain = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: b64ToBytes(env.iv) }, key, b64ToBytes(env.ct)
    );
    return JSON.parse(new TextDecoder().decode(plain));
  }

  /* 비밀번호 입력 화면. 맞을 때까지 붙잡고, 풀린 데이터를 돌려준다. */
  function promptUntilUnlocked(env) {
    return new Promise(function (resolve) {
      var wrap = document.createElement('div');
      wrap.setAttribute('style', [
        'position:fixed', 'inset:0', 'z-index:99999',
        'background:#0b1020', 'color:#e6edf3',
        'display:flex', 'align-items:center', 'justify-content:center',
        'font-family:system-ui,-apple-system,"Segoe UI",sans-serif'
      ].join(';'));

      wrap.innerHTML =
        '<div style="width:min(360px,88vw);text-align:center">' +
        '<div style="font-size:15px;font-weight:600;margin-bottom:6px">체크리스트 잠김</div>' +
        '<div style="font-size:13px;opacity:.65;margin-bottom:18px">비밀번호를 입력하세요</div>' +
        '<input id="clpw" type="password" autocomplete="current-password" ' +
        'style="width:100%;padding:12px 14px;border-radius:10px;border:1px solid #2a3550;' +
        'background:#131a2e;color:#e6edf3;font-size:15px;outline:none;box-sizing:border-box">' +
        '<div id="clerr" style="display:none;color:#ff6b6b;font-size:12px;margin-top:10px">' +
        '비밀번호가 맞지 않습니다</div>' +
        '<button id="clgo" style="width:100%;margin-top:12px;padding:12px;border:0;border-radius:10px;' +
        'background:#2563eb;color:#fff;font-size:14px;font-weight:600;cursor:pointer">열기</button>' +
        '</div>';

      document.body.appendChild(wrap);
      document.documentElement.style.visibility = '';

      var input = wrap.querySelector('#clpw');
      var err = wrap.querySelector('#clerr');
      var btn = wrap.querySelector('#clgo');
      input.focus();

      async function attempt() {
        var pw = input.value;
        if (!pw) return;
        btn.disabled = true;
        btn.textContent = '여는 중…';
        try {
          var data = await decryptEnvelope(env, pw);
          sessionStorage.setItem(PW_KEY, pw);
          wrap.remove();
          resolve(data);
        } catch (e) {
          sessionStorage.removeItem(PW_KEY);
          err.style.display = 'block';
          input.value = '';
          input.focus();
          btn.disabled = false;
          btn.textContent = '열기';
        }
      }

      btn.addEventListener('click', attempt);
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') attempt();
      });
    });
  }

  async function loadChecklistJson(url) {
    var res = await fetch(url + (url.indexOf('?') < 0 ? '?' : '&') + 't=' + Date.now());
    if (!res.ok) throw new Error('체크리스트를 받지 못했다: ' + res.status);
    var raw = await res.json();

    if (!raw || raw.encrypted !== true) return raw;  // 옛 평문 파일 하위호환

    var saved = sessionStorage.getItem(PW_KEY);
    if (saved) {
      try {
        return await decryptEnvelope(raw, saved);
      } catch (e) {
        sessionStorage.removeItem(PW_KEY);  // 비번이 바뀌었다 — 다시 묻는다
      }
    }
    return promptUntilUnlocked(raw);
  }

  global.loadChecklistJson = loadChecklistJson;
})(window);
