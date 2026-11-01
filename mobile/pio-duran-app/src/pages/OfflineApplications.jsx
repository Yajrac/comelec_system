import { useEffect, useState, useSyncExternalStore } from "react";
import { Link } from "react-router-dom";
import { getSyncState, subscribeSyncState } from "../services/syncState";
import { getSyncQueue, getSyncReceipts, removeFromSyncQueue } from "../services/offlineDatabase";
import { syncPendingRequests } from "../services/syncManager";
import "./OfflineApplications.css";

const label = value => value.replaceAll("_", " ");
const isDuplicate = item => item.status === "FAILED" && /already exists?|duplicate/i.test(item.lastError || "");
export default function OfflineApplications() {
    const state = useSyncExternalStore(subscribeSyncState, getSyncState);
    const [items, setItems] = useState([]);
    const [receipts, setReceipts] = useState([]);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState("");
    const [notice, setNotice] = useState("");
    const hasPendingUploads = items.some(item => item.status !== "FAILED");
    async function deleteSavedForm(item) {
        if (state.phase === "syncing" || deleting) return;
        if (!window.confirm("Delete this saved form and its attachments from this device? This will not delete any registration on the server.")) return;
        setDeleting(item.clientReference);
        setNotice("");
        try {
            await removeFromSyncQueue(item.clientReference);
            setNotice("Saved form deleted from this device.");
        } catch { setError("Unable to delete the saved form. Please try again."); }
        finally { setDeleting(""); }
    }
    useEffect(() => {
        let active = true;
        const load = async () => {
            try {
                const [queue, saved] = await Promise.all([getSyncQueue(), getSyncReceipts()]);
                if (active) { setItems(queue); setReceipts(saved); setError(""); }
            } catch { if (active) setError("Unable to read saved applications. Please try reopening this page."); }
            finally { if (active) setLoading(false); }
        };
        void load();
        window.addEventListener("offline-queue-changed", load);
        return () => { active = false; window.removeEventListener("offline-queue-changed", load); };
    }, [state]);

    return <main className="offline-applications">
        <div className="offline-page-heading"><div><h1>Offline Applications</h1><p>Review forms saved on this device and track their sync status.</p></div>
            {items.length > 0 && <button className="primary-button" type="button" disabled={!hasPendingUploads || state.phase === "offline" || state.phase === "syncing"} onClick={() => void syncPendingRequests()}>{state.phase === "syncing" ? "Syncing…" : "Sync now"}</button>}
        </div>
        {(error || state.error) && <p role="alert">{error || state.error}</p>}
        {notice && <p className="offline-action-notice" role="status">{notice}</p>}
        {loading ? <p role="status">Loading saved applications…</p> : !error && !items.length && <section className="offline-empty"><span aria-hidden="true">▤</span><h2>No offline applications yet</h2><p>Forms submitted while offline will appear here until they sync successfully.</p><Link to="/" className="primary-button">Go to Home</Link></section>}
        {items.map(item => <article className="offline-application-card" key={item.clientReference}>
            <div className="offline-card-heading"><h2>{label(item.requestType)}</h2><div className="offline-card-actions"><span className={`offline-status-badge${isDuplicate(item) ? " is-duplicate" : ""}`}>{isDuplicate(item) ? "Already exists" : item.status === "FAILED" ? "Needs attention" : item.status === "RETRYING" && state.phase === "syncing" ? "Uploading" : "Saved offline"}</span>
                {item.status === "FAILED" && <button className="offline-delete-button" type="button" aria-label={`Delete saved ${label(item.requestType)} form for ${item.payload.firstname || "applicant"}`} title="Delete saved form from this device" disabled={state.phase === "syncing" || !!deleting} onClick={() => void deleteSavedForm(item)}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7" /></svg></button>}
            </div></div>
            <strong>{[item.payload.lastname, item.payload.firstname, item.payload.middlename].filter(Boolean).join(" ") || "Applicant request"}</strong>
            <p>Saved {new Date(item.createdAt).toLocaleString()}</p>
            <p className="offline-local-reference">Local reference: {item.clientReference}</p>
            {item.lastError && <p role="status">{item.lastError}</p>}
            <details><summary>Review saved form</summary><dl className="offline-form-review">{Object.entries(item.payload).filter(([key]) => !["client_reference", "profile_details_provided"].includes(key)).map(([key, value]) => <div key={key}><dt>{label(key)}</dt><dd>{value?.mobileAttachment ? <><span>{value.name}</span>{value.type?.startsWith("image/") && <img src={value.dataUrl} alt={label(key)} loading="lazy" />}<a href={value.dataUrl} download={value.name}>Download attachment</a></> : typeof value === "boolean" ? value ? "Yes" : "No" : value == null || value === "" ? "Not provided" : String(value)}</dd></div>)}</dl></details>
        </article>)}
        {receipts.length > 0 && <section className="offline-receipts"><h2>Recently synced</h2>{receipts.map(receipt => <article key={receipt.clientReference}><strong>{label(receipt.requestType)}</strong><p>{receipt.data.registration_reference || `Request #${receipt.data.request_id || receipt.data.id || "submitted"}`}</p><small>Synced {new Date(receipt.syncedAt).toLocaleString()}</small></article>)}</section>}
    </main>;
}
