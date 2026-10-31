document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("reinstatementForm");
    const fileInput = document.getElementById("valid_id_document");
    const fileName = document.getElementById("selectedFileName");
    const submitButton = document.getElementById("submitButton");

    if (!form || !fileInput || !fileName || !submitButton) {
        return;
    }

    const allowedExtensions = ["pdf", "jpg", "jpeg", "png"];
    const maxFileSize = 5 * 1024 * 1024;

    fileInput.addEventListener("change", function () {
        const file = fileInput.files[0];

        if (!file) {
            fileName.textContent = "No file selected.";
            return;
        }

        const extension = file.name.includes(".")
            ? file.name.split(".").pop().toLowerCase()
            : "";

        if (!allowedExtensions.includes(extension)) {
            alert("Invalid file format. Please select a PDF, JPG, JPEG, or PNG file.");
            fileInput.value = "";
            fileName.textContent = "No file selected.";
            return;
        }

        if (file.size <= 0) {
            alert("The selected file is empty. Please choose another file.");
            fileInput.value = "";
            fileName.textContent = "No file selected.";
            return;
        }

        if (file.size > maxFileSize) {
            alert("The selected file exceeds the 5 MB limit.");
            fileInput.value = "";
            fileName.textContent = "No file selected.";
            return;
        }

        fileName.textContent =
            "Selected file: " + file.name +
            " (" + (file.size / (1024 * 1024)).toFixed(2) + " MB)";
    });

    form.addEventListener("submit", function (event) {
        const reason = document.getElementById("reason").value.trim();
        const file = fileInput.files[0];

        if (reason.length < 5 || reason.length > 2000) {
            event.preventDefault();
            alert("Please enter a reason between 5 and 2,000 characters.");
            document.getElementById("reason").focus();
            return;
        }

        if (file || fileInput.required) {
            if (!file) {
                event.preventDefault();
                alert("Please upload a valid ID document.");
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
                alert("Please select a non-empty ID document no larger than 5 MB.");
                fileInput.focus();
                return;
            }

        }

        submitButton.disabled = true;
        window.setApplicationSubmitting(submitButton);
    });
});
