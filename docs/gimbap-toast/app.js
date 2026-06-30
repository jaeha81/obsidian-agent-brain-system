(() => {
  'use strict';

  const data = window.STORE_DATA;
  if (!data) return;

  const bindText = () => {
    document.querySelectorAll('[data-bind]').forEach((node) => {
      const key = node.dataset.bind;
      if (Object.prototype.hasOwnProperty.call(data, key)) node.textContent = data[key];
    });

    document.querySelectorAll('[data-link]').forEach((node) => {
      const key = node.dataset.link;
      if (data[key]) node.href = data[key];
    });

    document.querySelectorAll('[data-tel]').forEach((node) => {
      const key = node.dataset.tel;
      const phone = String(data[key] || '').replace(/[^0-9+]/g, '');
      node.href = `tel:${phone}`;
    });
  };

  const renderKeywords = () => {
    const wrap = document.getElementById('heroKeywords');
    data.heroKeywords.forEach((keyword) => {
      const chip = document.createElement('span');
      chip.className = 'keyword-chip';
      chip.textContent = keyword;
      wrap.appendChild(chip);
    });
  };

  const categoryIcons = {
    gimbap: '◉',
    toast: '▱',
    meal: '♨',
    pocha: '✦'
  };

  const renderMenu = () => {
    const tabs = document.getElementById('menuTabs');
    const panel = document.getElementById('menuPanel');

    const showCategory = (category, selectedButton) => {
      tabs.querySelectorAll('[role="tab"]').forEach((button) => {
        const isSelected = button === selectedButton;
        button.setAttribute('aria-selected', String(isSelected));
        button.tabIndex = isSelected ? 0 : -1;
      });

      panel.setAttribute('aria-labelledby', `tab-${category.id}`);
      panel.innerHTML = `
        <div class="menu-panel-head">
          <div>
            <p>${category.eyebrow}</p>
            <h3>${category.label}</h3>
          </div>
          <span aria-hidden="true">${categoryIcons[category.id] || '•'}</span>
        </div>
        <ul class="menu-list">
          ${category.items.map((item) => `<li>${item}</li>`).join('')}
        </ul>
        <p class="menu-note">${category.note}</p>
      `;
    };

    data.categories.forEach((category, index) => {
      const button = document.createElement('button');
      button.className = 'menu-tab';
      button.id = `tab-${category.id}`;
      button.type = 'button';
      button.role = 'tab';
      button.tabIndex = index === 0 ? 0 : -1;
      button.setAttribute('aria-controls', 'menuPanel');
      button.setAttribute('aria-selected', String(index === 0));
      button.textContent = category.label;
      button.addEventListener('click', () => showCategory(category, button));
      button.addEventListener('keydown', (event) => {
        if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
        event.preventDefault();
        const allTabs = [...tabs.querySelectorAll('[role="tab"]')];
        const current = allTabs.indexOf(button);
        const direction = event.key === 'ArrowRight' ? 1 : -1;
        const next = allTabs[(current + direction + allTabs.length) % allTabs.length];
        next.focus();
        next.click();
      });
      tabs.appendChild(button);
    });

    showCategory(data.categories[0], tabs.firstElementChild);
  };

  let toastTimer;
  const showToast = (message) => {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
  };

  const copyAddress = async () => {
    try {
      await navigator.clipboard.writeText(data.address);
      showToast('주소가 복사되었습니다.');
    } catch {
      const input = document.createElement('textarea');
      input.value = data.address;
      input.style.position = 'fixed';
      input.style.opacity = '0';
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      input.remove();
      showToast('주소가 복사되었습니다.');
    }
  };

  const setupActions = () => {
    document.getElementById('copyAddress').addEventListener('click', copyAddress);
    document.getElementById('copyAddressSecondary').addEventListener('click', copyAddress);

    document.getElementById('shareButton').addEventListener('click', async () => {
      const shareData = {
        title: data.name,
        text: `${data.tagline}\n${data.address}`,
        url: data.naverMapUrl
      };
      try {
        if (navigator.share) {
          await navigator.share(shareData);
        } else {
          await navigator.clipboard.writeText(`${shareData.title}\n${shareData.text}\n${shareData.url}`);
          showToast('매장 정보가 복사되었습니다.');
        }
      } catch (error) {
        if (error?.name !== 'AbortError') showToast('공유 정보를 복사해 주세요.');
      }
    });

    const picker = document.getElementById('menuPicker');
    picker.addEventListener('click', () => {
      const result = data.randomMenus[Math.floor(Math.random() * data.randomMenus.length)];
      const output = document.getElementById('menuPickResult');
      output.textContent = `오늘의 추천은 “${result}”`; 
      picker.animate(
        [
          { transform: 'rotate(0deg) scale(1)' },
          { transform: 'rotate(-4deg) scale(.96)' },
          { transform: 'rotate(4deg) scale(1.03)' },
          { transform: 'rotate(0deg) scale(1)' }
        ],
        { duration: 380, easing: 'ease-out' }
      );
    });
  };

  const injectStructuredData = () => {
    const schema = {
      '@context': 'https://schema.org',
      '@type': 'Restaurant',
      name: data.name,
      alternateName: data.alternateName,
      description: data.description,
      telephone: data.phone,
      address: {
        '@type': 'PostalAddress',
        streetAddress: '하우고개길 90, 101동 102호',
        addressLocality: '파주시',
        addressRegion: '경기도',
        addressCountry: 'KR'
      },
      servesCuisine: ['분식', '김밥', '토스트', '한식', '포차'],
      priceRange: '₩',
      hasMap: data.naverMapUrl,
      sameAs: [data.instagramUrl, data.naverMapUrl]
    };
    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.textContent = JSON.stringify(schema);
    document.head.appendChild(script);
  };

  bindText();
  renderKeywords();
  renderMenu();
  setupActions();
  injectStructuredData();

  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
  }
})();
