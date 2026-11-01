import { useSyncExternalStore } from "react";
import { getSyncState, subscribeSyncState } from "../services/syncState";
import { useNavigate } from "react-router-dom";

const labels = { checking: "Checking…", offline: "Offline", syncing: "Syncing…", pending: "Sync pending", attention: "Sync needs attention", online: "Online" };

export default function ConnectionStatus() {
    const state = useSyncExternalStore(subscribeSyncState, getSyncState);
    const navigate = useNavigate();
    const displayPhase = state.phase === "attention" ? "online" : state.phase;
    return <div className="connection-status">
        <button type="button" className={`connection-badge connection-${displayPhase}`} onClick={() => navigate("/offline")} aria-label="View offline applications and sync status">
            {state.phase === "syncing" ? <span className="mobile-loading-spinner" aria-hidden="true" /> : <span className="connection-dot" aria-hidden="true" />}
            <span role="status" aria-live="polite">{labels[displayPhase]}{state.pending > 0 ? ` (${state.pending})` : ""}</span>
        </button>

    </div>;
}
