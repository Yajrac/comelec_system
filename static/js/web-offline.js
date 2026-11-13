/* Public web registration queue. No background upload, admin caching or installation UI. */
(() => {
    const panel = document.getElementById('webOfflinePanel');
    if (!panel) return;
    const message = document.getElementById('webOfflineMessage');
    const syncButton = document.getElementById('webSyncNow');
    const list = document.getElementById('webOfflineRecords');
    const form = document.getElementById('registrationForm');
    const owner = crypto.randomUUID();
    let database, online = false, running = false, draftId, revision = 0;
    let writes = Promise.resolve(), timer, queueing = false, submitting = false, storageReady = false;
    let editVersion = 0, dirty = false, saving = false;
    let syncFlight;
    let notifying = false;
    function confirmationUrl(record) {
        if (/^\/registration-success\/\d+\/$/.test(record.successUrl || '')) return record.successUrl;
        if (Number.isSafeInteger(record.applicantId) && record.applicantId > 0) return `/registration-success/${record.applicantId}/`;
        return null;
    }
    function resetSubmittedForm(id) {
        if (!form || draftId !== id) return;
        clearTimeout(timer); timer = null;
        form.reset();
        for (const name of ['lastname', 'firstname', 'middlename', 'birthdate', 'age', 'birthplace', 'phone', 'email', 'father', 'mother']) {
            const element = form.elements.namedItem(name);
            if (element) element.value = '';
        }
        document.getElementById('birthdate')?.dispatchEvent(new Event('offline:restore'));
        form.dispatchEvent(new Event('offline:submitted'));
        if (typeof window.backToForm === 'function') window.backToForm();
        draftId = crypto.randomUUID(); revision = 0; dirty = false;
        sessionStorage.setItem('web-registration-draft', draftId);
        history.replaceState(null, '', '/new-registration/');
    }
    // Uploads confirmed in this tab. Their local copies are already deleted, so the
    // reference shown in the success dialog is the applicant's only record of it.
    const confirmed = [];
    // Saved registrations the applicant chose to upload later (asked again on "Sync now").
    const laterIds = new Set();
    async function showSuccess() {
        const dialog = document.getElementById('webSyncSuccessDialog');
        if (!dialog || dialog.open || notifying) return;
        notifying = true;
        try {
            const references = document.getElementById('webSyncSuccessReferences');
            references.replaceChildren();
            const items = confirmed.splice(0);
            // Older versions kept confirmed uploads as "submitted"; show unseen ones once, then remove them.
            for (const record of await read()) {
                if (record.status !== 'submitted') continue;
                const claimed = await change(record.id, current => !current ? null : current.notificationSeen ? current : {...current, notificationSeen: true, notificationOwner: owner});
                if (claimed?.notificationOwner === owner && confirmationUrl(record)) items.push(record);
                await change(record.id, () => null);
            }
            for (const record of items) {
                resetSubmittedForm(record.id);
                const li = document.createElement('li');
                const reference = document.createElement('strong');
                reference.textContent = record.reference;
                li.append(reference);
                if (confirmationUrl(record)) {
                    const link = document.createElement('a');
                    link.className = 'offline-button'; link.href = confirmationUrl(record); link.textContent = 'View registration';
                    li.append(link);
                }
                references.append(li);
            }
            if (references.children.length) {
                await renderRecords();
                dialog.showModal();
            }
        } finally { notifying = false; }
    }
    // Reads a server reply. Non-JSON replies (Nginx 413 "too large", 502/504 gateway pages)
    // previously threw and left the record pending forever.
    async function interpret(response) {
        let data = null;
        try { data = await response.json(); } catch { data = null; }
        if (response.ok && data?.success && data.registration_reference) return {kind: 'success', data};
        if (response.status === 413) return {kind: 'invalid', error: 'The attached files are too large. Use smaller or compressed photos of your documents, then submit again.'};
        if (response.status >= 400 && response.status < 500 && ![408, 429].includes(response.status)) {
            return {kind: 'invalid', error: data?.error || data?.message || 'Please review the application.'};
        }
        return {kind: 'retry'};
    }
    function uploadBody(entries, reference) {
        const body = new FormData();
        for (const [name, value] of entries) body.append(name, value);
        body.set('client_reference', reference);
        return body;
    }
    function notice(text) {
        message.textContent = text;
        const formStatus = document.getElementById('webRegistrationStatus');
        if (formStatus) formStatus.textContent = text;
    }
    function fail(error) {
        notice(error.name === 'QuotaExceededError' ? 'Device storage is full. Your latest changes were not saved. Free space or submit online before leaving this page.' : error.message || 'Unable to access browser storage. Keep this page open and try again.');
    }
    function openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('applicant-web-offline', 1);
            request.onupgradeneeded = () => {
                request.result.createObjectStore('records', {keyPath: 'id'});
                request.result.createObjectStore('locks', {keyPath: 'id'});
            };
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }
    function read(id) {
        return new Promise((resolve, reject) => {
            const tx = database.transaction('records');
            const request = id ? tx.objectStore('records').get(id) : tx.objectStore('records').getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }
    function change(id, update) {
        return new Promise((resolve, reject) => {
            const tx = database.transaction('records', 'readwrite');
            const store = tx.objectStore('records');
            let result, failure;
            const request = store.get(id);
            request.onsuccess = () => {
                try {
                    result = update(request.result);
                    if (result === null) store.delete(id);
                    else store.put(result);
                } catch (error) { failure = error; tx.abort(); }
            };
            tx.oncomplete = () => resolve(result);
            tx.onabort = () => reject(failure || tx.error || new Error('Local save failed.'));
            tx.onerror = () => {};
        });
    }
    function snapshot() {
        return [...new FormData(form)].filter(([name, value]) => name !== 'csrfmiddlewaretoken' &&
            !(value instanceof File && !value.name));
    }
    async function saveDraft() {
        if (!storageReady || !form || queueing) return;
        const entries = snapshot();
        const version = editVersion;
        saving = true;
        let saved;
        try {
            saved = await change(draftId, current => {
                if (current && (current.revision !== revision || !['draft', 'needs-correction'].includes(current.status))) {
                    throw new Error('This application changed in another tab or was queued. Reopen it from Home before editing.');
                }
                return {id: draftId, entries, status: 'draft', revision: revision + 1, updated: Date.now()};
            });
        } finally { saving = false; }
        revision = saved.revision;
        if (version === editVersion) dirty = false;
        notice('Draft saved on this device. It has not been submitted.');
        await renderRecords();
    }
    function scheduleSave() {
        editVersion++;
        dirty = true;
        clearTimeout(timer);
        timer = setTimeout(() => { timer = null; writes = writes.then(saveDraft).catch(fail); }, 600);
    }
    function restore(entries) {
        for (const element of form.elements) {
            if (!element.name || element.name === 'csrfmiddlewaretoken') continue;
            const values = entries.filter(([name]) => name === element.name).map(([, value]) => value);
            if (element.type === 'file') {
                const transfer = new DataTransfer();
                values.filter(value => value instanceof Blob).forEach(file => transfer.items.add(file));
                element.files = transfer.files;
                element.dispatchEvent(new Event('change', {bubbles: true}));
            } else if (['checkbox', 'radio'].includes(element.type)) {
                element.checked = values.includes(element.value);
            } else if (values.length) element.value = values[0];
        }
        document.getElementById('birthdate')?.dispatchEvent(new Event('offline:restore'));
    }
    async function renderRecords() {
        const records = (await read()).sort((a, b) => b.updated - a.updated);
        list.replaceChildren();
        const pending = records.filter(record => ['pending', 'syncing'].includes(record.status)).length;
        syncButton.textContent = running ? 'Syncing…' : `Sync now (${pending})`;
        syncButton.setAttribute('aria-busy', String(running));
        syncButton.disabled = !online || running || !pending;
        for (const record of records) {
            const li = document.createElement('li');
            li.dataset.status = record.status;
            const title = document.createElement('strong');
            const field = name => record.entries?.find(([key]) => key === name)?.[1] || '';
            const labels = {'draft': 'Draft', 'pending': 'Pending sync', 'syncing': 'Syncing', 'submitted': 'Submitted', 'needs-correction': 'Needs correction'};
            title.textContent = `${labels[record.status]} — ${record.reference || [field('firstname'), field('lastname')].filter(Boolean).join(' ') || 'New registration'}`;
            li.append(title);
            {
                const icon = document.createElement('span');
                icon.className = 'web-offline-status-icon';
                icon.textContent = {draft: '\u270e', pending: '\u25f7', syncing: '', submitted: '\u2713', 'needs-correction': '!'}[record.status] || (record.status === 'syncing' ? '' : '!');
                icon.setAttribute('aria-hidden', 'true');
                const badge = document.createElement('span');
                badge.className = 'web-offline-status-badge';
                badge.textContent = labels[record.status];
                const label = document.createElement('span');
                label.className = 'web-offline-reference-label';
                label.textContent = record.status === 'submitted' ? 'Reference number' : 'Applicant';
                title.textContent = record.reference || [field('firstname'), field('lastname')].filter(Boolean).join(' ') || 'New registration';
                li.prepend(icon, badge, label);
            }
            const note = document.createElement('p');
            note.textContent = record.error || (record.status === 'submitted' ? 'Confirmed by the server. Local form data and attachments have been removed.' : 'Saved on this device. Not yet confirmed by the office.');
            li.append(note);
            if (['draft', 'needs-correction'].includes(record.status)) {
                const edit = document.createElement('a');
                edit.className = 'offline-button';
                edit.href = `/new-registration/?draft=${encodeURIComponent(record.id)}`;
                edit.textContent = 'Continue editing';
                li.append(edit);
            }
            if (record.status === 'submitted' && confirmationUrl(record)) {
                const view = document.createElement('a');
                view.className = 'offline-button'; view.href = confirmationUrl(record); view.textContent = 'View registration';
                li.append(view);
            }
            const remove = document.createElement('button');
            remove.type = 'button'; remove.className = 'web-offline-remove'; remove.textContent = '×';
            remove.setAttribute('aria-label', `Remove local ${labels[record.status].toLowerCase()} copy`);
            remove.title = 'Remove local copy';
            remove.disabled = record.status === 'syncing' || running;
            remove.addEventListener('click', async () => {
                if (!confirm('Remove this local copy? Unsynced information and attachments will be lost. This does not delete any server record.')) return;
                try {
                    if (record.id === draftId) {
                        queueing = true;
                        clearTimeout(timer); timer = null;
                        await writes;
                    }
                    await change(record.id, current => {
                        if (current?.status === 'syncing') throw new Error('Wait until sync finishes.');
                        return null;
                    });
                    if (record.id === draftId) {
                        dirty = false;
                        sessionStorage.removeItem('web-registration-draft');
                        location.href = '/new-registration/';
                    }
                    else await renderRecords();
                } catch (error) { queueing = false; fail(error); }
            });
            li.append(remove); list.append(li);
        }
    }
    async function checkConnection() {
        try {
            if (window.checkPublicConnection) online = await window.checkPublicConnection();
            else {
                const response = await fetch('/offline/connection/', {cache: 'no-store', signal: AbortSignal.timeout(8000)});
                online = response.ok && (await response.json()).online === true;
            }
        } catch { online = false; }
        return online;
    }
    function lease(release = false) {
        return new Promise((resolve, reject) => {
            const tx = database.transaction('locks', 'readwrite');
            const store = tx.objectStore('locks');
            let acquired = false;
            const request = store.get('sync');
            request.onsuccess = () => {
                const current = request.result;
                if (release) { if (current?.owner === owner) store.delete('sync'); }
                else if (!current || current.owner === owner || current.expires < Date.now()) {
                    store.put({id: 'sync', owner, expires: Date.now() + 90000}); acquired = true;
                }
            };
            tx.oncomplete = () => resolve(acquired);
            tx.onabort = () => reject(tx.error);
        });
    }
    function sync() {
        if (syncFlight) return syncFlight;
        syncFlight = performSync().finally(() => { syncFlight = null; });
        return syncFlight;
    }
    async function performSync() {
        if (!storageReady || running) return;
        running = true;
        syncButton.textContent = 'Syncing…';
        syncButton.setAttribute('aria-busy', 'true');
        syncButton.disabled = true;
        let acquired = false, heartbeat;
        try {
            if (!(await read()).some(record => ['pending', 'syncing'].includes(record.status))) return;
            if (!await checkConnection()) { notice('Offline. Pending applications remain saved on this device and will upload automatically when you are back online.'); return; }
            acquired = await lease();
            if (!acquired) { notice('Another tab is syncing, or a closed session is recovering. Retry in 90 seconds.'); return; }
            heartbeat = setInterval(() => lease().catch(fail), 20000);
            const records = await read();
            const queue = records.filter(record => ['pending', 'syncing'].includes(record.status) && !laterIds.has(record.id));
            let position = 0;
            for (const record of queue) {
                position++;
                // The applicant reviews each AI document check, so only check while the page is visible.
                if (window.documentCheck && document.hidden) break;
                const active = await change(record.id, current => {
                    if (!current || !['pending', 'syncing'].includes(current.status)) throw new Error('Queue changed. Retry sync.');
                    return {...current, status: 'syncing', updated: Date.now()};
                });
                await renderRecords();
                try {
                    if (window.documentCheck) {
                        const verdict = await window.documentCheck.reviewQueued(active.entries,
                            queue.length > 1 ? ` (${position} of ${queue.length})` : '');
                        if (verdict === 'later') {
                            laterIds.add(active.id);
                            await change(active.id, current => ({...current, status: 'pending', updated: Date.now()}));
                            notice('Upload postponed. Press Sync now when you are ready.');
                            continue;
                        }
                        if (verdict?.fix) {
                            await change(active.id, current => ({...current, status: 'needs-correction', error: verdict.fix, updated: Date.now()}));
                            continue;
                        }
                    }
                    const response = await fetch('/api/new-registration/', {method: 'POST', body: uploadBody(active.entries, active.id), signal: AbortSignal.timeout(60000), credentials: 'same-origin'});
                    const result = await interpret(response);
                    if (result.kind === 'success') {
                        const {data} = result;
                        // Confirmed by the server: drop the local copy and its attachments.
                        await change(active.id, () => null);
                        confirmed.push({id: active.id, reference: data.registration_reference, applicantId: data.applicant_id, successUrl: data.success_url});
                        notice('Application uploaded successfully.');
                    } else if (result.kind === 'invalid') {
                        await change(active.id, current => ({...current, status: 'needs-correction', error: result.error, updated: Date.now()}));
                    } else throw new Error('The server could not confirm this application. It remains saved for retry.');
                } catch (error) {
                    await change(active.id, current => ({...current, status: 'pending', error: 'Not confirmed. Retry sync when the connection is stable. The same submission ID will be reused.', updated: Date.now()}));
                    notice('Sync interrupted. Pending data is saved; retry will not create another copy of the same submission.');
                    break;
                }
            }
        } catch (error) { fail(error); }
        finally {
            clearInterval(heartbeat);
            if (acquired) await lease(true).catch(fail);
            running = false;
            await renderRecords().catch(fail);
            if (!submitting) await showSuccess().catch(fail);
        }
    }
    window.webOfflineRegistration = {
        async submit(currentForm, button) {
            if (queueing || submitting) return;
            submitting = true;
            button.disabled = true;
            clearTimeout(timer);
            timer = null;
            try {
                // Online: upload directly; the form only goes to the offline queue if this fails.
                if (await checkConnection()) {
                    notice('Uploading your application…');
                    let result;
                    try {
                        const response = await fetch('/api/new-registration/', {method: 'POST', body: uploadBody(snapshot(), draftId),
                            signal: AbortSignal.timeout(60000), credentials: 'same-origin'});
                        result = await interpret(response);
                    } catch { result = {kind: 'retry'}; }
                    if (result.kind === 'success') {
                        queueing = true;
                        if (storageReady) {
                            await writes.catch(() => {});
                            await change(draftId, () => null).catch(() => {});
                        }
                        sessionStorage.removeItem('web-registration-draft');
                        dirty = false;
                        location.href = result.data.success_url || '/';
                        return;
                    }
                    if (result.kind === 'invalid') {
                        notice(result.error);
                        if (typeof window.backToForm === 'function') window.backToForm();
                        return;
                    }
                    // Connection dropped or server unavailable: fall through and queue it. The same
                    // client_reference is reused, so a save that reached the server is not duplicated.
                }
                if (!storageReady) throw new Error('No connection and browser storage is not ready. Your form has not been saved. Keep this page open and try again.');
                await writes;
                await saveDraft();
                if (syncFlight) await syncFlight;
                queueing = true;
                await change(draftId, current => {
                    if (!current || current.revision !== revision || current.status !== 'draft') throw new Error('Reopen the saved draft before submitting.');
                    return {...current, status: 'pending', updated: Date.now()};
                });
                sessionStorage.removeItem('web-registration-draft');
                notice('No connection. Saved on this device; it will upload automatically when you are back online.');
                location.href = '/offline/';
            } catch (error) { fail(error); queueing = false; }
            finally { button.disabled = false; submitting = false; }
        }
    };
    async function prepareOffline() {
        const ready = document.getElementById('webOfflineReady');
        function readiness(state, text) {
            ready.dataset.state = state;
            ready.textContent = text;
        }
        if (!('serviceWorker' in navigator) || !window.isSecureContext) {
            readiness('error', 'Offline page reopening is unavailable in this browser. Keep the form open.'); return;
        }
        try {
            const registration = await navigator.serviceWorker.register('/web-offline-sw.js', {scope: '/'});
            const report = () => readiness('ready', 'Home, New Registration and Offline are ready to reopen offline.');
            if (registration.active) report();
            else {
                readiness('preparing', 'Preparing Home and New Registration for offline use. Stay online until ready.');
                const worker = registration.installing || registration.waiting;
                worker?.addEventListener('statechange', () => {
                    if (worker.state === 'activated') report();
                    if (worker.state === 'redundant') readiness('error', 'Offline download failed. Reopen Home online to retry.');
                });
            }
        } catch { readiness('error', 'Offline page download unavailable. Keep this page open and retry online.'); }
    }
    (async () => {
        try {
            database = await openDatabase(); storageReady = true;
            if (form) {
                const requested = new URL(location.href).searchParams.get('draft');
                draftId = requested || sessionStorage.getItem('web-registration-draft') || crypto.randomUUID();
                const record = await read(draftId);
                if (record && ['draft', 'needs-correction'].includes(record.status)) {
                    restore(record.entries); revision = record.revision;
                    notice('Saved draft restored, including attachments. Review it before submitting.');
                } else if (record || requested) {
                    draftId = crypto.randomUUID();
                    notice('That draft is unavailable or already queued. A new form is ready.');
                } else notice('Your answers are saved on this device automatically. You can also submit while offline once the offline pages are ready.');
                sessionStorage.setItem('web-registration-draft', draftId);
                form.addEventListener('input', scheduleSave);
                form.addEventListener('change', scheduleSave);
                form.addEventListener('submit', event => {
                    event.preventDefault();
                    if (form.reportValidity()) window.submitApplication();
                });
                // Drafts save automatically on every change (scheduleSave), so no manual button.
                window.addEventListener('beforeunload', event => {
                    if (!queueing && (dirty || saving)) { event.preventDefault(); event.returnValue = ''; }
                });
            } else notice('Drafts and pending submissions saved in this browser appear below.');
            await renderRecords();
            document.getElementById('webSyncSuccessClose')?.addEventListener('click', () => document.getElementById('webSyncSuccessDialog').close());
            await showSuccess();
            await prepareOffline();
            await sync();
            syncButton.addEventListener('click', () => { laterIds.clear(); sync(); });
            // The network is often not usable the instant the "online" event fires, so retry a few times.
            window.addEventListener('online', () => {
                for (const delay of [0, 3000, 10000, 30000]) setTimeout(() => sync().catch(fail), delay);
            });
            document.addEventListener('visibilitychange', () => { if (!document.hidden) sync().catch(fail); });
            window.addEventListener('offline', () => { online = false; renderRecords().catch(fail); });
            setInterval(sync, 60000);
        } catch (error) { storageReady = false; syncButton.disabled = true; fail(error); }
    })();
})();
