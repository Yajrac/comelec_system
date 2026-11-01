import { useEffect, useRef } from "react";
import "./LookupModal.css";

export default function LookupModal({ checking, message, onClose }) {
    const dialog = useRef(null);
    useEffect(() => {
        if (checking || message) {
            if (!dialog.current.open) dialog.current.showModal();
        } else dialog.current.close();
    }, [checking, message]);
    return <dialog ref={dialog} className="lookup-modal" aria-labelledby="lookup-modal-title" onCancel={event => { if (checking) event.preventDefault(); else onClose(); }}>
        {checking && <span className="mobile-loading-spinner" aria-hidden="true" />}
        <h2 id="lookup-modal-title">{checking ? "Checking registration…" : "Unable to continue"}</h2>
        <p role="status">{checking ? "Checking your registration and existing application requests. Please wait." : message}</p>
        {!checking && <button type="button" className="primary-button" onClick={onClose} autoFocus>OK</button>}
    </dialog>;
}
