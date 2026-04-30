(function () {
  if (!('wakeLock' in navigator)) return;

  let lock = null;

  async function acquire() {
    try {
      lock = await navigator.wakeLock.request('screen');
    } catch (e) {
      // permissions, low battery, etc — no-op
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') acquire();
  });

  acquire();
})();
