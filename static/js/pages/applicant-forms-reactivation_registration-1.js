"use strict";

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("reactivationForm");
    const fileInput = document.getElementById("valid_id_document");
    const filePreview = document.getElementById("filePreview");
    const reason = document.getElementById("reason");
    const submitButton = document.getElementById("submitReactivation");

    const allowedExtensions = ["pdf", "jpg", "jpeg", "png"];
    const maxFileSize = 5 * 1024 * 1024;

    if (fileInput && filePreview) {
        fileInput.addEventListener("change", function () {
            filePreview.textContent = "";
            filePreview.classList.remove("visible");

            const file = this.files && this.files[0];

            if (!file) {
                return;
            }

            const extension = file.name.includes(".")
                ? file.name.split(".").pop().toLowerCase()
                : "";

            if (!allowedExtensions.includes(extension)) {
                this.value = "";
                alert(
                    "Invalid file type. Please select a PDF, JPG, JPEG, or PNG file."
                );
                return;
            }

            if (file.size <= 0) {
                this.value = "";
                alert("The selected file is empty. Please choose another file.");
                return;
            }

            if (file.size > maxFileSize) {
                this.value = "";
                alert("The valid ID file must not exceed 5 MB.");
                return;
            }

            filePreview.textContent =
                "Selected file: " + file.name +
                " (" + (file.size / (1024 * 1024)).toFixed(2) + " MB)";

            filePreview.classList.add("visible");
        });
    }

    if (form) {
        form.addEventListener("submit", function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                form.reportValidity();
                return;
            }

            const file = fileInput.files && fileInput.files[0];

            if (file || fileInput.required) {
                if (!file) {
                    event.preventDefault();
                    alert("Please upload your valid ID.");
                    fileInput.focus();
                    return;
                }

                const extension = file.name.includes(".")
                    ? file.name.split(".").pop().toLowerCase()
                    : "";

                if (!allowedExtensions.includes(extension)) {
                    event.preventDefault();
                    alert("Please upload a PDF, JPG, JPEG, or PNG file.");
                    fileInput.focus();
                    return;
                }

                if (file.size <= 0 || file.size > maxFileSize) {
                    event.preventDefault();
                    alert("Please select a non-empty ID file no larger than 5 MB.");
                    fileInput.focus();
                    return;
                }

            }

            if (reason.value.trim().length < 5) {
                event.preventDefault();
                alert("Please provide a more detailed reason for reactivation.");
                reason.focus();
                return;
            }

            if (submitButton) {
                submitButton.disabled = true;
                window.setApplicationSubmitting(submitButton);
            }
        });
    }
});
