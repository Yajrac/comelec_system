let state = { phase: "checking", pending: 0, failed: 0, items: [], receipts: [], error: "" };
const listeners = new Set();
export const getSyncState = () => state;
export function subscribeSyncState(listener) { listeners.add(listener); return () => listeners.delete(listener); }
export function publishSyncState(updates) {
    state = { ...state, ...updates };
    listeners.forEach(listener => listener());
}
