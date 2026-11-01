import { useState } from "react";
import axios from "axios";
import LookupModal from "./LookupModal";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function ReferenceLookup({ type, children }) {
    const [reference, setReference] = useState("");
    const [applicant, setApplicant] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    async function find(event) {
        event.preventDefault();
        setError("");
        const value = reference.trim().toUpperCase();
        if (!/^PD-[A-F0-9]{32}$/.test(value)) {
            setError("Enter PD- followed by exactly 32 hexadecimal characters."); return;
        }
        setLoading(true);
        try {
            const response = await axios.post(`${API}/api/applicants/find/`, { registration_reference: value, request_type: type }, { timeout: 15000 });
            const found = response.data.applicant;
            if (!found) throw new Error("No registration was found for this reference number.");
            if (["REACTIVATION", "REINSTATEMENT"].includes(type) && found.is_active) {
                setError("This registration is already active."); return;
            }
            if (type === "TRANSFER" && (!found.is_active || found.status !== "APPROVED")) {
                setError("Transfer requires an approved, active registration."); return;
            }
            setApplicant(found);
        } catch (failure) {
            setError(failure.response?.data?.error || failure.message || "Unable to find your registration. Please try again.");
        } finally { setLoading(false); }
    }
    if (applicant) return <><div className="reference-found"><strong>Registration found</strong><p>{applicant.lastname}, {applicant.firstname} {applicant.middlename} {applicant.suffix}</p><p>{applicant.registration_reference}</p><button type="button" className="secondary-button" onClick={() => setApplicant(null)}>Search another reference</button></div>{children(applicant)}</>;
    return (
        <main className="verify-main"><LookupModal checking={loading} message={error} onClose={() => setError("")} /><div className="verify-container">
            <div className="page-header"><h1>Find Your Registration</h1><p>Enter the registration reference number you received when you registered.</p></div>
            <section className="verify-card"><div className="card-header-government"><h2>Registration Reference Number</h2></div><div className="card-body-government">
                <form onSubmit={find}>
                    <label htmlFor="registration_reference" className="form-label">Registration Reference Number <span className="required">*</span></label>
                    <input id="registration_reference" name="registration_reference" className="form-control" value={reference} onChange={event => { setReference(event.target.value.toUpperCase()); setError(""); }} placeholder="PD-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" maxLength={35} required autoCapitalize="characters" autoCorrect="off" spellCheck={false} aria-describedby="reference-help reference-error" />
                    <p id="reference-help" className="form-text">Use the reference number shown on your registration confirmation.</p>
                    {error && <p id="reference-error" className="form-error" role="alert">{error}</p>}
                    <div className="form-actions"><button type="submit" className="primary-button" disabled={loading || !reference.trim()} aria-busy={loading}>{loading && <span className="mobile-loading-spinner" aria-hidden="true" />}{loading ? "Searching..." : "Find Registration"}</button></div>
                </form>
            </div></section>
        </div></main>
    );
}
