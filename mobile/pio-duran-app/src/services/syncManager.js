import { API_BASE_URL as API_URL } from "./apiConfig";
import axios from "axios";
import { Network } from "@capacitor/network";
import { toRequestBody } from "./requestPayload";
import { getSyncQueue, removeFromSyncQueue, updateQueueItem, getSyncReceipts, saveSyncReceipt } from "./offlineDatabase";
import { publishSyncState } from "./syncState";
import { loadCachedBarangays } from "./barangayCache";


let onlineStatus = navigator.onLine;
let running = false;
let generation = 0;
let listener;
let timer;
let flight;
let rerun = false;
export function isOnline() { return onlineStatus; }
async function refreshNetworkStatus() {
    try { onlineStatus = Boolean((await Network.getStatus()).connected); }
    catch { onlineStatus = navigator.onLine; }
    return onlineStatus;
}
async function publishQueue(error = "") {
    const items = await getSyncQueue();
    const receipts = await getSyncReceipts();
    const failed = items.filter(item => item.status === "FAILED").length;
    const pending = items.length - failed;
    const phase = !onlineStatus ? "offline" : error || failed ? "attention" : pending ? "pending" : "online";
    publishSyncState({ phase, pending, failed, items, receipts, error });
}
async function performSync() {
    publishSyncState({ phase: "syncing", error: "" });
    try {
        if (!await refreshNetworkStatus()) { await publishQueue(); return; }
        const queue = await getSyncQueue();
        for (const item of queue.filter(value => value.status !== "FAILED")) {
            if (!running || !await refreshNetworkStatus()) break;
            await updateQueueItem(item.clientReference, { status: "RETRYING", attempts: (item.attempts || 0) + 1, lastAttemptAt: new Date().toISOString() });
            try {
                const response = await axios.post(`${API_URL}${item.endpoint}`, toRequestBody({ ...item.payload, client_reference: item.clientReference }), { timeout: 30000 });
                if (!response.data?.success) throw { response: { status: 400, data: response.data } };
                // Save the server receipt before deleting the local files and request.
                await saveSyncReceipt(item, response.data);
                await removeFromSyncQueue(item.clientReference);
            } catch (error) {
                const rejected = [400, 404, 409, 422].includes(error.response?.status);
                await updateQueueItem(item.clientReference, { status: rejected ? "FAILED" : "WAITING", lastError: error.response?.data?.error || error.message || "Unable to connect to the server." });
                if (!error.response) { onlineStatus = false; break; }
            }
        }
        await publishQueue();
    } catch (error) {
        publishSyncState({ phase: onlineStatus ? "attention" : "offline", error: error.message || "Unable to read offline storage." });
    }
}
export function syncPendingRequests() {
    if (flight) { rerun = true; return flight; }
    flight = performSync().finally(() => {
        flight = null;
        if (rerun && running && onlineStatus) { rerun = false; void syncPendingRequests(); }
        else rerun = false;
    });
    return flight;
}
function connected() { onlineStatus = true; void loadCachedBarangays().catch(() => {}); void syncPendingRequests(); }
function disconnected() { onlineStatus = false; publishSyncState({ phase: "offline" }); }
function queueChanged(event) {
    // Status updates within a sync must not schedule another upload attempt.
    if (event?.triggerSync === false) return;
    if (flight) rerun = true;
    else void syncPendingRequests();
}
function resume() { if (!document.hidden) void syncPendingRequests(); }
export async function startSyncManager() {
    if (running) return;
    running = true;
    const current = ++generation;
    window.addEventListener("online", connected);
    window.addEventListener("offline", disconnected);
    window.addEventListener("offline-queue-changed", queueChanged);
    document.addEventListener("visibilitychange", resume);
    try {
        const added = await Network.addListener("networkStatusChange", status => status.connected ? connected() : disconnected());
        if (current !== generation || !running) { await added.remove(); return; }
        listener = added;
    } catch { /* Browser events remain active. */ }
    if (current !== generation || !running) return;
    timer = setInterval(() => { if (!document.hidden) void syncPendingRequests(); }, 30000);
    void loadCachedBarangays().catch(() => {});
    await syncPendingRequests();
}
export async function stopSyncManager() {
    running = false;
    generation += 1;
    clearInterval(timer);
    window.removeEventListener("online", connected);
    window.removeEventListener("offline", disconnected);
    window.removeEventListener("offline-queue-changed", queueChanged);
    document.removeEventListener("visibilitychange", resume);
    const old = listener;
    listener = null;
    if (old) await old.remove();
}
export const initSyncManager = startSyncManager;
