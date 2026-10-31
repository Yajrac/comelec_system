"use strict";

/* =========================================================
   DOCUMENT VIEWER
========================================================= */

function openDocumentViewer() {
    const modal = document.getElementById("documentViewerModal");
    const body = document.getElementById("documentViewerBody");

    if (!modal || !body) {
        return;
    }

    const documentUrl = modal.dataset.documentUrl;

    const extension = documentUrl
        .split("?")[0]
        .split("#")[0]
        .split(".")
        .pop()
        .toLowerCase();

    body.replaceChildren();

    if (["jpg", "jpeg", "png"].includes(extension)) {
        const image = document.createElement("img");

        image.src = documentUrl;
        image.alt = "Uploaded valid ID or supporting document";

        image.onerror = function () {
            body.replaceChildren();

            const message = document.createElement("div");
            message.className = "document-unavailable";
            message.textContent =
                "The image could not be displayed. Try opening the document in a new tab.";

            body.appendChild(message);
        };

        body.appendChild(image);

    } else if (extension === "pdf") {
        const iframe = document.createElement("iframe");

        iframe.src = documentUrl;
        iframe.title = "Uploaded PDF document";

        body.appendChild(iframe);

    } else {
        const message = document.createElement("div");

        message.className = "document-unavailable";
        message.textContent =
            "This file format cannot be previewed. Use Open in New Tab instead.";

        body.appendChild(message);
    }

    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    const closeButton = modal.querySelector(".document-viewer-close");

    if (closeButton) {
        closeButton.focus();
    }
}

function closeDocumentViewer() {
    const modal = document.getElementById("documentViewerModal");
    const body = document.getElementById("documentViewerBody");

    if (!modal) {
        return;
    }

    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";

    if (body) {
        body.replaceChildren();
    }

    const viewButton = document.getElementById("viewDocumentButton");

    if (viewButton) {
        viewButton.focus();
    }
}

/* Close popup using Escape */
document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
        closeDocumentViewer();
    }
});

/* Close popup by clicking the dark background */
document.addEventListener("click", function (event) {
    const modal = document.getElementById("documentViewerModal");

    if (modal && event.target === modal) {
        closeDocumentViewer();
    }
});
