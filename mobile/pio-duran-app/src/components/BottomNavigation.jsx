import { NavLink } from "react-router-dom";
import { useSyncExternalStore } from "react";
import { getSyncState, subscribeSyncState } from "../services/syncState";
import "../pages/OfflineApplications.css";

export default function BottomNavigation() {
    const state = useSyncExternalStore(subscribeSyncState, getSyncState);
    return <nav className="app-bottom-navigation" aria-label="Main navigation">
        <NavLink to="/" end><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7v10H14v-6h-4v6H3Z" /></svg><span>Home</span></NavLink>
        <NavLink to="/offline"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v16H4ZM8 4v6h8V4M8 20v-6h8v6" /></svg><span>Offline {state.items.length > 0 && <b>{state.items.length}</b>}</span></NavLink>
    </nav>;
}
