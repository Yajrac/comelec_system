import { Preferences } from "@capacitor/preferences";

const SYNC_QUEUE_KEY = "offline_sync_queue";
const RECEIPTS_KEY = "offline_sync_receipts";
let mutations = Promise.resolve();
function mutate(transform, triggerSync = true) {
    const operation = mutations.then(async () => {
        const queue = await getSyncQueue();
        await Preferences.set({ key: SYNC_QUEUE_KEY, value: JSON.stringify(transform(queue)) });
        const event = new Event("offline-queue-changed");
        event.triggerSync = triggerSync;
        window.dispatchEvent(event);
    });
    mutations = operation.catch(() => {});
    return operation;
}
export async function initOfflineDatabase() { await getSyncQueue(); return true; }
export function generateClientReference(type) {
    return `${String(type).replace(/[^A-Z0-9]/gi, "").toUpperCase()}-${Date.now()}-${crypto.randomUUID()}`;
}
export async function getSyncQueue() {
    const { value } = await Preferences.get({ key: SYNC_QUEUE_KEY });
    if (!value) return [];
    const queue = JSON.parse(value);
    if (!Array.isArray(queue)) throw new Error("Offline request storage could not be read.");
    return queue;
}
export function addToSyncQueue({ requestType, endpoint, payload, clientReference }) {
    return mutate(queue => queue.some(item => item.clientReference === clientReference) ? queue : [...queue, {
        id: clientReference, requestType, endpoint, payload, clientReference, status: "WAITING", attempts: 0,
        createdAt: new Date().toISOString(), lastAttemptAt: null, lastError: null,
    }]);
}
export function removeFromSyncQueue(reference) { return mutate(queue => queue.filter(item => item.clientReference !== reference)); }
export function updateQueueItem(reference, updates) { return mutate(queue => queue.map(item => item.clientReference === reference ? { ...item, ...updates } : item), false); }
export function clearSyncQueue() { return mutate(() => []); }
export async function getPendingRequestCount() { return (await getSyncQueue()).filter(item => item.status !== "FAILED").length; }
export async function getFailedRequestCount() { return (await getSyncQueue()).filter(item => item.status === "FAILED").length; }
export async function getSyncReceipts() {
    const { value } = await Preferences.get({ key: RECEIPTS_KEY });
    return value ? JSON.parse(value) : [];
}
export async function saveSyncReceipt(item, data) {
    const receipts = await getSyncReceipts();
    const receipt = { clientReference: item.clientReference, requestType: item.requestType,
        data, syncedAt: new Date().toISOString() };
    await Preferences.set({ key: RECEIPTS_KEY, value: JSON.stringify([receipt, ...receipts.filter(value => value.clientReference !== item.clientReference)].slice(0, 50)) });
}
