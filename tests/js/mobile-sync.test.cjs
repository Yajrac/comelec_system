const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const { webcrypto } = require('node:crypto');

function load(name, context) {
    let source = fs.readFileSync(path.join(__dirname, '../../mobile/pio-duran-app/src/services', name + '.js'), 'utf8');
    const exports = [...source.matchAll(/export\s+(?:async\s+)?(?:function|const)\s+(\w+)/g)].map(match => match[1]);
    source = source.replace(/^import[\s\S]*?;\s*/gm, '').replace(/import\.meta\.env\.VITE_API_URL/g, 'undefined').replace(/export\s+(?=(?:async\s+)?function|const)/g, '');
    return vm.runInNewContext(`(function(){${source}\nreturn {${exports.join(',')}};})()`, context);
}

function setup() {
    const storage = new Map();
    let connected = false;
    let networkChanged;
    const context = {
        window: new EventTarget(), document: Object.assign(new EventTarget(), { hidden: false }),
        navigator: { onLine: false }, Event, crypto: webcrypto, Blob, File, FormData,
        setInterval: () => 1, clearInterval() {},
        Preferences: { get: async ({ key }) => ({ value: storage.get(key) || null }),
            set: async ({ key, value }) => { storage.set(key, value); } },
        Network: { getStatus: async () => ({ connected }), addListener: async (name, callback) => { networkChanged = callback; return { remove() {} }; } },
        axios: { post: async () => ({ status: 201, data: { success: true, registration_reference: 'PD-' + 'A'.repeat(32) } }),
            get: async () => ({ data: [{ id: 1, name: 'Test Barangay' }] }) },
        loadCachedBarangays: async () => [], toRequestBody: value => value,
    };
    const state = load('syncState', context);
    Object.assign(context, state);
    const queue = load('offlineDatabase', context);
    Object.assign(context, queue);
    const manager = load('syncManager', context);
    return { context, state, queue, manager, storage, connect(value) {
        connected = value; context.navigator.onLine = value;
        networkChanged?.({ connected: value });
    } };
}

const item = reference => ({ requestType: 'NEW_REGISTRATION', endpoint: '/api/new-registration/',
    clientReference: reference, payload: { firstname: 'Juan' } });
const tick = () => new Promise(resolve => setImmediate(resolve));

test('server errors wait for the next scheduled retry instead of restarting sync immediately', async () => {
    const app = setup();
    await app.queue.addToSyncQueue(item('server-error-retry'));
    await app.manager.startSyncManager();
    let attempts = 0;
    app.context.axios.post = async () => {
        attempts++;
        throw { response: { status: 503, data: { error: 'Server unavailable' } } };
    };
    app.connect(true);
    await tick();
    await tick();
    await app.manager.stopSyncManager();
    assert.equal(attempts, 1);
    assert.equal((await app.queue.getSyncQueue())[0].status, 'WAITING');
    assert.equal(app.state.getSyncState().phase, 'pending');
});

test('offline registration remains saved; header stays Syncing until the server confirms it', async () => {
    const app = setup();
    await app.queue.addToSyncQueue(item('offline-new-one'));
    await app.manager.startSyncManager();
    assert.equal(app.state.getSyncState().phase, 'offline');
    let confirm;
    app.context.axios.post = () => new Promise(resolve => { confirm = resolve; });
    app.connect(true);
    await tick();
    assert.equal(app.state.getSyncState().phase, 'syncing');
    assert.equal((await app.queue.getSyncQueue()).length, 1);
    confirm({ status: 201, data: { success: true, registration_reference: 'PD-' + 'A'.repeat(32) } });
    await app.manager.syncPendingRequests();
    await tick();
    assert.equal(app.state.getSyncState().phase, 'online');
    assert.equal((await app.queue.getSyncQueue()).length, 0);
    assert.equal((await app.queue.getSyncReceipts())[0].data.registration_reference, 'PD-' + 'A'.repeat(32));
    await app.manager.stopSyncManager();
});

test('server rejection retains the request and shows attention instead of Online', async () => {
    const app = setup();
    await app.queue.addToSyncQueue(item('offline-rejected'));
    await app.manager.startSyncManager();
    app.context.axios.post = async () => { throw { response: { status: 400, data: { error: 'Duplicate registration.' } } }; };
    app.connect(true);
    await tick();
    await app.manager.syncPendingRequests();
    await tick();
    const queued = await app.queue.getSyncQueue();
    assert.equal(queued[0].status, 'FAILED');
    assert.equal(queued[0].lastError, 'Duplicate registration.');
    assert.equal(app.state.getSyncState().phase, 'attention');
    await app.manager.stopSyncManager();
});

test('network failure keeps the request for a later retry', async () => {
    const app = setup();
    await app.queue.addToSyncQueue(item('offline-retry'));
    await app.manager.startSyncManager();
    app.context.axios.post = async () => { throw new Error('Network unavailable'); };
    app.connect(true);
    await tick();
    const queued = await app.queue.getSyncQueue();
    assert.equal(queued[0].status, 'WAITING');
    assert.equal(app.state.getSyncState().phase, 'offline');
    await app.manager.stopSyncManager();
});

test('concurrent local additions and removals do not lose other requests', async () => {
    const { queue } = setup();
    await Promise.all([queue.addToSyncQueue(item('one')), queue.addToSyncQueue(item('two'))]);
    await Promise.all([queue.removeFromSyncQueue('one'), queue.addToSyncQueue(item('three'))]);
    assert.deepEqual(Array.from(await queue.getSyncQueue(), value => value.clientReference).sort(), ['three', 'two']);
});

test('barangay list is cached online and remains available offline', async () => {
    const app = setup();
    const cache = load('barangayCache', app.context);
    app.connect(true);
    assert.equal((await cache.loadCachedBarangays())[0].name, 'Test Barangay');
    app.connect(false);
    app.context.axios.get = async () => { throw new Error('Must not fetch offline'); };
    assert.equal((await cache.loadCachedBarangays())[0].id, 1);
});

test('first offline launch explains that the barangay list must be downloaded once', async () => {
    const app = setup();
    const cache = load('barangayCache', app.context);
    await assert.rejects(cache.loadCachedBarangays(), /Connect to the internet once/);
});

test('New Registration submission saves real attachments offline and syncs after reconnect', async () => {
    const app = setup();
    app.context.FileReader = class {
        async readAsDataURL(file) {
            this.result = `data:${file.type};base64,${Buffer.from(await file.arrayBuffer()).toString('base64')}`;
            this.onload();
        }
    };
    app.context.atob = atob;
    Object.assign(app.context, load('requestPayload', app.context), { isOnline: app.manager.isOnline });
    const requests = load('apiRequest', app.context);
    await app.manager.startSyncManager();
    const saved = await requests.submitWithOfflineSupport({ requestType: 'NEW_REGISTRATION',
        endpoint: '/api/new-registration/', payload: { firstname: 'Juan', profile_details_provided: '1',
            photo: new File(['photo-bytes'], 'photo.png', { type: 'image/png' }),
            valid_id_document: new File(['%PDF-1.7'], 'id.pdf', { type: 'application/pdf' }) } });
    assert.equal(saved.offline, true);
    assert.equal((await app.queue.getSyncQueue())[0].payload.photo.mobileAttachment, true);
    let uploaded;
    app.context.axios.post = async (url, body) => {
        uploaded = body;
        return { status: 201, data: { success: true, registration_reference: 'PD-' + 'B'.repeat(32) } };
    };
    app.connect(true);
    await app.manager.syncPendingRequests();
    await tick();
    assert.equal(await uploaded.get('photo').text(), 'photo-bytes');
    assert.equal(await uploaded.get('valid_id_document').text(), '%PDF-1.7');
    assert.equal(app.state.getSyncState().phase, 'online');
    assert.equal((await app.queue.getSyncQueue()).length, 0);
    await app.manager.stopSyncManager();
});
