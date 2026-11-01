export function initialRequestProfile(applicant) {
    return { suffix: applicant?.suffix || "", is_indigenous: Boolean(applicant?.is_indigenous),
        is_illiterate: Boolean(applicant?.is_illiterate), photo: null, valid_id_document: null,
        profile_details_provided: "1" };
}

export function requestProfileError(profile, applicant) {
    if (!["", "Jr.", "Sr.", "II", "III", "IV", "V"].includes(profile.suffix)) return "Select a valid suffix.";
    if (!profile.valid_id_document && !applicant?.has_valid_id_document) return "Upload your Valid ID and Birth Certificate.";
    for (const key of ["photo", "valid_id_document"]) {
        const file = profile[key];
        if (!file) continue;
        if (file.size > 5 * 1024 * 1024) return "Each file must be 5 MB or smaller.";
        const allowed = key === "photo" ? /\.(jpe?g|png)$/i : /\.(pdf|jpe?g|png)$/i;
        if (!allowed.test(file.name)) return key === "photo" ? "Upload a JPG or PNG photo." : "Upload a PDF, JPG, or PNG document.";
    }
    return "";
}

