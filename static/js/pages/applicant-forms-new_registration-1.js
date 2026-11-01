"use strict";

const MAX_DOCUMENT_SIZE = 5 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"];

function getValue(id) {
    const element = document.getElementById(id);
    return element ? element.value.trim() : "";
}

function getSelectedText(id) {
    const element = document.getElementById(id);

    if (!element || element.selectedIndex < 0) {
        return "";
    }

    return element.options[element.selectedIndex].text;
}

function setReview(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value || "-";
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) {
        return bytes + " bytes";
    }

    if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + " KB";
    }

    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

/* DOCUMENT VALIDATION */
function validateDocument() {
    const input = document.getElementById("valid_id_document");
    const error = document.getElementById("documentError");
    const info = document.getElementById("documentFileInfo");
    const fileName = document.getElementById("documentFileName");
    const fileSize = document.getElementById("documentFileSize");

    const file = input.files && input.files.length
        ? input.files[0]
        : null;

    input.classList.remove("is-invalid");
    error.style.display = "none";
    error.textContent = "";
    info.style.display = "none";

    if (!file) {
        input.classList.add("is-invalid");
        error.textContent =
            "Please select a valid ID or supporting document.";
        error.style.display = "block";
        return false;
    }

    const lastDot = file.name.lastIndexOf(".");
    const extension = lastDot >= 0
        ? file.name.substring(lastDot).toLowerCase()
        : "";

    if (!ALLOWED_EXTENSIONS.includes(extension)) {
        input.classList.add("is-invalid");
        error.textContent =
            "Invalid file type. Upload PDF, JPG, JPEG, or PNG.";
        error.style.display = "block";
        return false;
    }

    if (file.size <= 0) {
        input.classList.add("is-invalid");
        error.textContent =
            "The selected file is empty. Please choose another file.";
        error.style.display = "block";
        return false;
    }

    if (file.size > MAX_DOCUMENT_SIZE) {
        input.classList.add("is-invalid");
        error.textContent =
            "The file exceeds 5 MB. Please select a smaller document.";
        error.style.display = "block";
        return false;
    }

    fileName.textContent = file.name;
    fileSize.textContent = "File size: " + formatFileSize(file.size);
    info.style.display = "block";

    setReview("review_document_name", file.name);
    setReview(
        "review_document_size",
        "File size: " + formatFileSize(file.size)
    );

    return true;
}

document.getElementById("valid_id_document").addEventListener(
    "change",
    validateDocument
);

/* PHONE VALIDATION */
function validatePhoneNumber() {
    const phoneInput = document.getElementById("phone");
    const phoneError = document.getElementById("phoneError");
    const phone = phoneInput.value.trim();

    phoneInput.classList.remove("is-invalid");
    phoneError.style.display = "none";
    phoneError.textContent = "";

    if (!phone) {
        phoneInput.classList.add("is-invalid");
        phoneError.textContent = "Phone number is required.";
        phoneError.style.display = "block";
        return false;
    }

    if (!/^09[0-9]{9}$/.test(phone)) {
        phoneInput.classList.add("is-invalid");
        phoneError.textContent =
            "Enter a valid 11-digit Philippine mobile number.";
        phoneError.style.display = "block";
        return false;
    }

    return true;
}

document.getElementById("phone").addEventListener("input", function () {
    this.value = this.value.replace(/\D/g, "").substring(0, 11);
    validatePhoneNumber();
});

/* BIRTHDATE VALIDATION */
(function setBirthdateMaximum() {
    const birthdateInput = document.getElementById("birthdate");
    const today = new Date();

    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");

    birthdateInput.max = `${year}-${month}-${day}`;
})();

/* SHOW REVIEW */
function showReview() {
    const form = document.getElementById("registrationForm");

    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    if (!validatePhoneNumber()) {
        document.getElementById("phone").focus();
        return;
    }

    if (!validateDocument()) {
        document.getElementById("valid_id_document").focus();
        return;
    }

    setReview("review_lastname", getValue("lastname"));
    setReview("review_firstname", getValue("firstname"));

    // Optional middle name: display a dash when left blank.
    setReview("review_middlename", getValue("middlename"));

    setReview("review_suffix", getValue("suffix") || "None");
    setReview("review_is_indigenous", document.getElementById("is_indigenous").checked ? "Yes" : "No");
    setReview("review_is_illiterate", document.getElementById("is_illiterate").checked ? "Yes" : "No");
    const photo = document.getElementById("photo").files[0];
    setReview("review_photo", photo ? photo.name : "No photo selected");
    const photoPreview = document.getElementById("photoPreview");
    const reviewPhoto = document.getElementById("review_photo_preview");
    reviewPhoto.hidden = !photo || photoPreview.hidden;
    if (!reviewPhoto.hidden) reviewPhoto.src = photoPreview.src;
    else reviewPhoto.removeAttribute("src");
    setReview("review_age", getValue("age"));
    setReview("review_sex", getSelectedText("sex"));
    setReview("review_birthdate", getValue("birthdate"));
    setReview("review_birthplace", getValue("birthplace"));
    setReview("review_civil_status", getSelectedText("civil_status"));

    setReview("review_brgy", getSelectedText("brgy"));

    setReview("review_phone", getValue("phone"));

    // Optional email: display a dash when left blank.
    setReview("review_email", getValue("email"));

    setReview("review_pwd_status", getSelectedText("pwd_status"));
    setReview(
        "review_citizenship_status",
        getSelectedText("citizenship_status")
    );
    setReview("review_father", getValue("father"));
    setReview("review_mother", getValue("mother"));

    const fileInput = document.getElementById("valid_id_document");
    const file = fileInput.files.length ? fileInput.files[0] : null;

    setReview(
        "review_document_name",
        file ? file.name : "No document selected"
    );

    setReview(
        "review_document_size",
        file ? "File size: " + formatFileSize(file.size) : ""
    );

    document.getElementById("formScreen").style.display = "none";
    document.getElementById("reviewScreen").style.display = "block";

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}

/* BACK TO EDIT */
function backToForm() {
    document.getElementById("reviewScreen").style.display = "none";
    document.getElementById("formScreen").style.display = "block";

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}

/* SUBMIT REGISTRATION */
function submitApplication() {
    const form = document.getElementById("registrationForm");

    if (!form.checkValidity()) {
        backToForm();
        form.reportValidity();
        return;
    }

    if (!validatePhoneNumber()) {
        backToForm();
        document.getElementById("phone").focus();
        return;
    }

    if (!validateDocument()) {
        backToForm();
        document.getElementById("valid_id_document").focus();
        return;
    }

    const applicationType = form.querySelector(
        'input[name="application_type"]'
    );

    if (applicationType) {
        applicationType.value = "NEW";
    }

    const submitButton = document.getElementById("submitButton");

    submitButton.disabled = true;
    window.setApplicationSubmitting(submitButton);

    HTMLFormElement.prototype.submit.call(form);
}
