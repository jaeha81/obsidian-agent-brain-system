/* JH shared nav — inject into nav.jh-nav elements */
(function () {
  var LINKS = [
    { href: '/repo/',              label: '레포대시보드' },
    { href: '/bucky-brain.html',   label: '시스템상태', cls: 'sys-status' },
    { href: '/wishket/',           label: '위시켓' },
    { href: '/daily-plus/',        label: '오늘의플러스' },
    { href: '/task-board/',        label: '태스크보드' },
    { href: '/claude-code/',       label: 'Claude앱' },
    { href: '/codex/',             label: 'Codex' },
    { href: '/chris/',             label: 'Chris' },
    { href: '/charlie/',           label: 'Charlie' },
    { href: '/my-dev/',            label: '내소개' },
    { href: '/shorts/',            label: '쇼츠' },
    { href: '/chsh-mining/',       label: 'CHSH마이닝' },
    { href: '/threads/',           label: '쓰레드자동화' },
    { href: '/kmong/',             label: '크몽' },
    { href: '/workflow/',          label: '워크플로우' },
    { href: '/ai-usage.html',      label: 'AI사용량' },
    { href: '/wiki-gate.html',     label: 'Wiki Gate' },
    { href: '/estimation-dashboard.html', label: '견적분석' },
    { href: '/bucky-os.html',      label: 'BuckyOS' },
    { href: '/system-enhance.html', label: '시스템강화', cls: 'sys-enhance' },
    { href: '/system-evolution.html', label: '시스템진화', cls: 'sys-evo' },
    { href: '/api/logout',         label: '로그아웃', cls: 'auth-end' },
  ];

  function isActive(href) {
    var p = location.pathname;
    return href.endsWith('/') ? (p === href || p.startsWith(href)) : p === href;
  }

  function render() {
    var navs = document.querySelectorAll('nav.jh-nav');
    navs.forEach(function (nav) {
      nav.innerHTML = LINKS.map(function (l) {
        var active = isActive(l.href);
        var cls = active && l.cls ? 'active ' + l.cls : active ? 'active' : (l.cls || '');
        var attrs = cls ? ' class="' + cls + '"' : '';
        return '<a href="' + l.href + '"' + attrs + '>' + l.label + '</a>';
      }).join('\n    ');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
