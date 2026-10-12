(() => {
  'use strict';
  const button = document.getElementById('installApp');
  const status = document.getElementById('installStatus');
  let promptEvent = null;
  const standalone = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  const say = text => { if (status) status.textContent = text; };
  const refresh = () => {
    if (button) button.hidden = standalone();
    if (!navigator.onLine) say('Çevrimdışısınız. Ekrandaki veriler güncellenemez; internet bağlantısı gerekli.');
    else if (standalone()) say('Uygulama açık. Verilerin kapanış tarihini ve doğrulama durumunu kontrol edin.');
    else say('Telefona ekleyerek tek dokunuşla açabilirsiniz. İnternet bağlantısı gerekir.');
  };
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    promptEvent = event;
    if (button) button.hidden = false;
  });
  if (button) button.addEventListener('click', async () => {
    if (promptEvent) {
      const pending = promptEvent;
      promptEvent = null;
      try {
        await pending.prompt();
        const choice = await pending.userChoice;
        say(choice.outcome === 'accepted' ? 'Kurulum kabul edildi. Ana ekranınızdaki BIST Terminal simgesini kullanın.' : 'Kurulum iptal edildi; terminali tarayıcıdan kullanabilirsiniz.');
      } catch (_) { say('Chrome ⋮ menüsü → Ana ekrana ekle / Uygulamayı yükle.'); }
    } else if (/iPhone|iPad|iPod/i.test(navigator.userAgent)) {
      say('Safari: Paylaş → Ana Ekrana Ekle.');
    } else {
      say('Android Chrome: ⋮ menüsü → Ana ekrana ekle / Uygulamayı yükle. Uygulama içi tarayıcıdaysanız önce Chrome’da açın.');
    }
  });
  window.addEventListener('appinstalled', () => { promptEvent = null; refresh(); say('BIST Terminal kuruldu. Ana ekran simgesinden açabilirsiniz.'); });
  window.addEventListener('offline', refresh);
  window.addEventListener('online', refresh);
  refresh();
  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('./sw.js', {scope: './', updateViaCache: 'none'})
      .catch(() => say('Uygulama kurulumu şu an kullanılamıyor. Terminali bu tarayıcıdan kullanabilirsiniz.'));
  }
})();
