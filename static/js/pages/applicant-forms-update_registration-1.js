document.addEventListener("DOMContentLoaded", function () {
    const fileInput = document.getElementById("valid_id_document");
    const fileName = document.getElementById("documentFileName");
    const fileError = document.getElementById("documentUploadError");
    const updateForm = document.getElementById("updateRegistrationForm");
    const submitButton = document.getElementById("submitUpdateButton");

    const preview = document.getElementById("replacementDocumentPreview");
    let previewUrl;
    window.addEventListener("pagehide", () => { if (previewUrl) URL.revokeObjectURL(previewUrl); });
    const MAX_FILE_SIZE = 5 * 1024 * 1024;
    const ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png"];

    if (fileInput) {
        fileInput.addEventListener("change", function () {
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            if (preview) { preview.hidden = true; preview.removeAttribute("href"); }
            fileError.textContent = "";
            fileName.textContent = "";

            const file = fileInput.files && fileInput.files[0];

            if (!file) {
                return;
            }

            const extension = file.name.split(".").pop().toLowerCase();

            if (!ALLOWED_EXTENSIONS.includes(extension)) {
                fileError.textContent =
                    "Invalid file format. Please select a PDF, JPG, JPEG, or PNG file.";
                fileInput.value = "";
                return;
            }

            if (file.size > MAX_FILE_SIZE) {
                fileError.textContent =
                    "The selected file exceeds the 5 MB limit. Please choose a smaller file.";
                fileInput.value = "";
                return;
            }

            if (file.size === 0) {
                fileError.textContent =
                    "The selected file is empty. Please choose another file.";
                fileInput.value = "";
                return;
            }

            previewUrl = URL.createObjectURL(file);
            if (preview) { preview.href = previewUrl; preview.hidden = false; }
            fileName.textContent =
                "Selected file: " + file.name +
                " (" + (file.size / (1024 * 1024)).toFixed(2) + " MB)";
        });
    }

    if (updateForm) {
        updateForm.addEventListener("submit", function (event) {
            if (fileError) {
                fileError.textContent = "";
            }

            if (fileInput && (fileInput.required || fileInput.files.length)) {
                const file = fileInput.files && fileInput.files[0];

                if (!file) {
                    event.preventDefault();
                    fileError.textContent =
                        "Please upload a valid ID or supporting document before submitting.";
                    fileInput.focus();
                    return;
                }

                const extension = file.name.split(".").pop().toLowerCase();

                if (!ALLOWED_EXTENSIONS.includes(extension)) {
                    event.preventDefault();
                    fileError.textContent =
                        "Invalid file format. Please select a PDF, JPG, JPEG, or PNG file.";
                    fileInput.focus();
                    return;
                }

                if (file.size === 0 || file.size > MAX_FILE_SIZE) {
                    event.preventDefault();
                    fileError.textContent =
                        "The file must not be empty or larger than 5 MB.";
                    fileInput.focus();
                    return;
                }
            }

            if (!updateForm.checkValidity()) {
                event.preventDefault();
                updateForm.reportValidity();
                return;
            }

            if (submitButton) {
                submitButton.disabled = true;
                window.setApplicationSubmitting(submitButton);
            }
        });
    }

    const phoneInput = document.getElementById("phone");

    if (phoneInput) {
        phoneInput.addEventListener("input", function () {
            this.value = this.value.replace(/\D/g, "").slice(0, 11);
        });
    }
});
