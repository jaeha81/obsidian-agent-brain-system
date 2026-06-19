/* auth.js — 매 접속 로그인 강제 + 새로고침 시 로그아웃
 * 모든 내부 페이지 <head> 안에 blocking 로드 (defer/async 금지)
 */
(function () {
  var LOGIN = '/login.html';

  function clearCookie() {
    document.cookie = 'bucky_auth=; Max-Age=0; Path=/; SameSite=Strict';
    document.cookie = 'bucky_auth=; Max-Age=0; Path=/; SameSite=Strict; Secure';
  }

  function goLogin() {
    var redirect = encodeURIComponent(location.pathname + location.search);
    location.replace(LOGIN + '?redirect=' + redirect);
  }

  // 새로고침 감지 → 쿠키 삭제 후 로그인
  var isReload = false;
  try {
    var nav = performance.getEntriesByType('navigation');
    if (nav.length && nav[0].type === 'reload') isReload = true;
  } catch (e) {}

  if (isReload) {
    clearCookie();
    goLogin();
    return;
  }

  // 쿠키 없으면 로그인
  if (!/(?:^|;\s*)bucky_auth=\S/.test(document.cookie)) {
    goLogin();
  }
})();
