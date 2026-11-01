// Keep attachments intact when requests are stored in the JSON offline queue.
export async function serializeRequestPayload(payload) {
    const result = { ...payload };
    for (const [key, value] of Object.entries(result)) {
        if (!(value instanceof Blob)) continue;
        const dataUrl = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error("Could not save the attachment. Please select it again."));
            reader.readAsDataURL(value);
        });
        result[key] = { mobileAttachment: true, name: value.name, type: value.type, dataUrl };
    }
    return result;
}

export function toRequestBody(payload) {
    const multipart = payload.profile_details_provided || Object.values(payload).some(value => value instanceof Blob || value?.mobileAttachment);
    if (!multipart) return payload;
    const body = new FormData();
    for (const [key, raw] of Object.entries(payload)) {
        let value = raw;
        if (value?.mobileAttachment) {
            const bytes = Uint8Array.from(atob(value.dataUrl.split(",")[1]), char => char.charCodeAt(0));
            value = new File([bytes], value.name, { type: value.type });
        }
        if (value == null || value === false) continue;
        body.append(key, value === true ? "on" : value);
    }
    return body;
}
