/* auth.js — 로그인 강제 (모바일 호환)
 * 모든 내부 페이지 <head> 안에 blocking 로드 (defer/async 금지)
 * 참고: isReload 감지는 모바일에서 탭복원/앱복귀를 reload로 인식해 무한루프 유발 → 제거
 */
(function () {
  var LOGIN = '/login.html';

  function goLogin() {
    var redirect = encodeURIComponent(location.pathname + location.search);
    location.replace(LOGIN + '?redirect=' + redirect);
  }

  if (!/(?:^|;\s*)bucky_auth=\S/.test(document.cookie)) {
    goLogin();
  }
})();
