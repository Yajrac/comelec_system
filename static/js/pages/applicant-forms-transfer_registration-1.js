document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("transferForm");
    const submitButton = document.getElementById("submitTransferButton");
    const reason = document.getElementById("reason");

    const fileInput = document.getElementById("valid_id_document");
    const fileStatus = document.getElementById("valid-id-status");
    const fileError = document.getElementById("valid-id-error");

    const allowedExtensions = ["pdf", "jpg", "jpeg", "png"];
    const maxFileSize = 5 * 1024 * 1024;

    function validateIdFile() {
        if (!fileInput) {
            return false;
        }

        const file = fileInput.files[0];

        if (fileError) {
            fileError.textContent = "";
        }

        if (fileStatus) {
            fileStatus.className = "file-status";
            fileStatus.textContent = "No file selected.";
        }

        if (!file && !fileInput.required) return true;
        if (!file) {
            if (fileError) {
                fileError.textContent = "Please upload a valid ID.";
            }

            if (fileStatus) {
                fileStatus.classList.add("error");
            }

            return false;
        }

        const parts = file.name.split(".");
        const extension = parts.length > 1
            ? parts.pop().toLowerCase()
            : "";

        if (!allowedExtensions.includes(extension)) {
            if (fileError) {
                fileError.textContent =
                    "Invalid file type. Select a PDF, JPG, JPEG, or PNG file.";
            }

            if (fileStatus) {
                fileStatus.classList.add("error");
                fileStatus.textContent = "Unsupported file format.";
            }

            return false;
        }

        if (file.size > maxFileSize) {
            if (fileError) {
                fileError.textContent =
                    "The ID file must not exceed 5 MB.";
            }

            if (fileStatus) {
                fileStatus.classList.add("error");
                fileStatus.textContent = "File exceeds the 5 MB limit.";
            }

            return false;
        }

        if (file.size === 0) {
            if (fileError) {
                fileError.textContent =
                    "The selected file is empty. Please choose another file.";
            }

            if (fileStatus) {
                fileStatus.classList.add("error");
                fileStatus.textContent = "Empty file.";
            }

            return false;
        }

        if (fileStatus) {
            fileStatus.classList.add("success");
            fileStatus.textContent =
                "Selected: " + file.name +
                " (" + (file.size / 1024).toFixed(1) + " KB)";
        }

        return true;
    }

    if (fileInput) {
        fileInput.addEventListener("change", validateIdFile);
    }

    if (reason) {
        reason.addEventListener("input", function () {
            this.setCustomValidity("");
        });
    }

    if (form) {
        form.addEventListener("submit", function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                form.reportValidity();
                return;
            }

            if (reason && reason.value.trim().length < 5) {
                event.preventDefault();

                reason.setCustomValidity(
                    "Please provide a more detailed reason for the transfer."
                );

                reason.reportValidity();
                reason.setCustomValidity("");
                return;
            }

            if (!validateIdFile()) {
                event.preventDefault();

                if (fileInput) {
                    fileInput.focus();
                }

                return;
            }

            if (submitButton) {
                submitButton.disabled = true;
                window.setApplicationSubmitting(submitButton);
            }
        });
    }
});
