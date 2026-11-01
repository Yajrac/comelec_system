import { useEffect, useRef } from "react";

export default function RegistrationPhoto({ file, onChange, existingUrl }) {
    const camera = useRef(null);
    const preview = useRef(null);
    useEffect(() => {
        if (!file) return;
        const url = URL.createObjectURL(file);
        if (preview.current) preview.current.src = url;
        return () => URL.revokeObjectURL(url);
    }, [file]);
    function takePhoto(event) {
        const selected = event.target.files[0];
        if (!selected) return;
        const extension = selected.name.split(".").pop().toLowerCase();
        const name = `${new Date().toISOString().replace(/[:.]/g, "-")}.${extension}`;
        onChange(new File([selected], name, { type: selected.type }));
        event.target.value = "";
    }
    return (
        <section className="mobile-photo-section">
            <h2>Photo / Selfie</h2>
            <div className="mobile-photo-body">
                <label htmlFor="registrationPhoto" className="form-label">Upload Photo or Selfie (optional)</label>
                <input id="registrationPhoto" type="file" name="photo" accept=".jpg,.jpeg,.png,image/jpeg,image/png" onChange={event => onChange(event.target.files[0] || null)} />
                <input ref={camera} type="file" accept="image/jpeg,image/png" capture="user" hidden onChange={takePhoto} />
                <button type="button" className="secondary-button mobile-camera-button" onClick={() => camera.current.click()}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M8 6 10 3h4l2 3h4v14H4V6Z" /><circle cx="12" cy="12" r="4" /></svg>
                    {file ? "Retake Selfie" : "Take Selfie"}
                </button>
                <p className="form-text">Upload a clear photo or use your device camera. JPG or PNG, maximum 5 MB.</p>
                {file && <img ref={preview} alt="Selected applicant photo" className="mobile-photo-preview" />}
                {!file && existingUrl && <><img src={existingUrl} alt="Existing applicant photo" className="mobile-photo-preview" /><p className="form-text">Leave this empty to keep your existing photo.</p></>}
            </div>
        </section>
    );
}
