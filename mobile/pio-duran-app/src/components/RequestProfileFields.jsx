import RegistrationPhoto from "./RegistrationPhoto";

export default function RequestProfileFields({ profile, setProfile, applicant, part = "profile" }) {
    const change = event => {
        const { name, type, checked, value } = event.target;
        setProfile(previous => ({ ...previous, [name]: type === "checkbox" ? checked : value }));
    };
    const flags = (
            <fieldset className="mobile-profile-flags"><legend>Additional Information (optional)</legend>
                <label><input type="checkbox" name="is_indigenous" checked={profile.is_indigenous} onChange={change} />Indigenous People</label>
                <label><input type="checkbox" name="is_illiterate" checked={profile.is_illiterate} onChange={change} />Illiterate (unable to read and write)</label>
            </fieldset>
    );
    if (part === "flags") return flags;
    if (part === "photo") return <RegistrationPhoto file={profile.photo} existingUrl={applicant?.photo_url} onChange={photo => setProfile(previous => ({ ...previous, photo }))} />;
    if (part === "documents") return (
        <section className="form-section"><h3 className="section-title">Upload Valid ID and Birth Certificate</h3>
            {applicant?.has_valid_id_document && <p className="form-text">An existing document is on file. Leave this empty to keep it, or select a replacement.</p>}
            <label htmlFor="request_document" className="form-label">Upload Valid ID and Birth Certificate{applicant?.has_valid_id_document ? " (optional)" : " *"}</label>
            <input id="request_document" type="file" name="valid_id_document" className="form-control" accept=".pdf,.jpg,.jpeg,.png" required={!profile.valid_id_document && !applicant?.has_valid_id_document} onChange={event => setProfile(previous => ({ ...previous, valid_id_document: event.target.files[0] || null }))} />
            <p className="form-text">Accepted formats: PDF, JPG, JPEG, PNG. Maximum file size: 5 MB.</p>
        </section>
    );
    return <div className="mobile-request-profile">
        <RegistrationPhoto file={profile.photo} existingUrl={applicant?.photo_url} onChange={photo => setProfile(previous => ({ ...previous, photo }))} />
        <section className="form-section"><h3 className="section-title">Personal Information</h3>
            <div className="form-group mobile-request-suffix"><label htmlFor="request_suffix">Suffix (optional)</label><select id="request_suffix" name="suffix" value={profile.suffix} onChange={change}><option value="">None</option>{["Jr.", "Sr.", "II", "III", "IV", "V"].map(value => <option key={value}>{value}</option>)}</select></div>
            {flags}
        </section>

    </div>;
}
