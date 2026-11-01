import { useEffect, useId, useRef, useState } from "react";
import "./BirthdateInput.css";
import { birthdateEligibility } from "../utils/birthdateEligibility";

const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export default function BirthdateInput({ value = "", onChange, required = false, electionDate = "" }) {
    const id = useId();
    const [year, month, day] = value.split("-");
    const [parts, setParts] = useState({ year: year || "", month: month ? String(Number(month)) : "", day: day ? String(Number(day)) : "" });
    const emitted = useRef(value);
    const yearInput = useRef(null);
    const currentYear = new Date().getFullYear();
    const eligibility = birthdateEligibility(value, electionDate);
    useEffect(() => {
        if (value) yearInput.current.setCustomValidity(eligibility?.error || "");
    }, [value, electionDate, eligibility?.error]);

    useEffect(() => {
        if (value === emitted.current) return;
        const [y, m, d] = value.split("-");
        setParts({ year: y || "", month: m ? String(Number(m)) : "", day: d ? String(Number(d)) : "" });
        emitted.current = value;
    }, [value]);

    function change(key, text) {
        const next = { ...parts, [key]: key === "year" ? text.replace(/\D/g, "").slice(0, 4) : text };
        setParts(next);
        const complete = next.year.length === 4 && next.month && next.day;
        const date = new Date(Number(next.year), Number(next.month) - 1, Number(next.day));
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        let error = "";
        if (next.year.length === 4 && (Number(next.year) < 1900 || Number(next.year) > currentYear)) error = "Enter a valid birth year from 1900 to the current year.";
        else if (complete && date.getMonth() !== Number(next.month) - 1) error = "Choose a valid day for this month and year.";
        else if (complete && date >= today) error = "Birthdate must be earlier than today.";
        yearInput.current.setCustomValidity(error);
        const iso = complete && !error ? `${next.year}-${next.month.padStart(2, "0")}-${next.day.padStart(2, "0")}` : "";
        emitted.current = iso;
        onChange({ target: { name: "birthdate", value: iso } });
    }

    return <><div className="mobile-birthdate" role="group" aria-label="Birthdate: month, day, year">
        <span className="mobile-birthdate-icon" aria-hidden="true"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M7 3v4m10-4v4M3 11h18" /></svg></span>
        <label><span>Month</span><select aria-label="Birthdate month" autoComplete="bday-month" required={required} value={parts.month} onChange={event => change("month", event.target.value)}><option value="">Month</option>{months.map((name, index) => <option key={name} value={index + 1}>{name}</option>)}</select></label>
        <label><span>Day</span><select aria-label="Birthdate day" autoComplete="bday-day" required={required} value={parts.day} onChange={event => change("day", event.target.value)}><option value="">Day</option>{Array.from({ length: 31 }, (_, index) => <option key={index} value={index + 1}>{index + 1}</option>)}</select></label>
        <label><span>Year</span><input ref={yearInput} aria-label="Birthdate year" type="text" inputMode="numeric" autoComplete="bday-year" placeholder="YYYY" maxLength={4} pattern="[0-9]{4}" list={id} required={required} value={parts.year} onChange={event => change("year", event.target.value)} /></label>
        <datalist id={id}>{Array.from({ length: currentYear - 1899 }, (_, index) => <option key={index} value={currentYear - index} />)}</datalist>
    </div>
        {eligibility && <small className={`mobile-birthdate-eligibility${eligibility.eligible ? "" : " is-ineligible"}`} role="status" aria-live="polite">{eligibility.message}</small>}
        {!electionDate && <small className="mobile-birthdate-pending" role="status">You can continue. Election eligibility will be checked by the server when your application is submitted or synced.</small>}
    </>;
}
