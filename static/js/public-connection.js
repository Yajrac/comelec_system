(() => {
    const badge = document.getElementById('publicConnectionBadge');
    if (!badge) return;
    const label = document.getElementById('publicConnectionLabel');
    let flight;
    function update(online) {
        badge.dataset.state = online ? 'online' : 'offline';
        label.textContent = online ? 'Online' : 'Offline';
        badge.title = online ? 'Connected to the server' : 'Server unreachable. Pending applications remain on this device.';
        return online;
    }
    window.checkPublicConnection = () => {
        if (flight) return flight;
        flight = (async () => {
            try {
                const response = await fetch('/offline/connection/', {cache: 'no-store', signal: AbortSignal.timeout(8000)});
                return update(response.ok && (await response.json()).online === true);
            } catch { return update(false); }
        })().finally(() => { flight = null; });
        return flight;
    };
    window.addEventListener('online', window.checkPublicConnection);
    window.addEventListener('offline', () => update(false));
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) window.checkPublicConnection();
    });
    setInterval(window.checkPublicConnection, 60000);
    window.checkPublicConnection();
})();
