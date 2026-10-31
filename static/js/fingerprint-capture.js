document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const config = document.getElementById("csrfForm");
    if (!config) return;
    const startCaptureUrl = config.dataset.startCaptureUrl;
    const captureStatusUrlTemplate = config.dataset.captureStatusUrl;

    const leftButton =
        document.getElementById("captureLeftFinger");

    const rightButton =
        document.getElementById("captureRightFinger");

    const savedFingers = {
        left: {
            image: config.dataset.leftImage === "true",
            template: config.dataset.leftTemplate === "true"
        },
        right: {
            image: config.dataset.rightImage === "true",
            template: config.dataset.rightTemplate === "true"
        }
    };

    function getCsrfToken() {
        const input = document.querySelector(
            "#csrfForm input[name='csrfmiddlewaretoken']"
        );
        return input ? input.value : "";
    }

    async function parseResponse(response) {
        const raw = await response.text();
        let data;

        try {
            data = JSON.parse(raw);
        } catch (error) {
            console.error("Unexpected server response:", raw);
            throw new Error(
                `Invalid server response (HTTP ${response.status}).`
            );
        }

        if (!response.ok) {
            throw new Error(
                data.message ||
                data.error ||
                `Request failed (HTTP ${response.status}).`
            );
        }

        return data;
    }

    function setMessage(element, text, type = "info") {
        element.className = "bio-message" + (type ? " " + type : "");
        element.textContent = text;
    }

    function setStatus(element, text, type = "") {
        element.className = "bio-status" + (type ? " " + type : "");
        element.textContent = text;
    }

    function showPlaceholder(
        preview,
        iconName,
        headingText,
        descriptionText
    ) {
        preview.replaceChildren();

        const wrapper = document.createElement("div");
        wrapper.className = "bio-placeholder";

        const icon = document.createElement("i");
        icon.className = "bi " + iconName;

        const heading = document.createElement("strong");
        heading.textContent = headingText;

        const description = document.createElement("span");
        description.textContent = descriptionText;

        wrapper.append(icon, heading, description);
        preview.appendChild(wrapper);
        preview.classList.remove("captured");
    }

    function getFingerButtonLabel(finger) {
        const alreadySaved = savedFingers[finger].image;
        const fingerName =
            finger === "left" ? "Left" : "Right";

        const label = alreadySaved
            ? `Recapture ${fingerName} Finger`
            : `Capture ${fingerName} Finger`;

        return '<i class="bi bi-fingerprint me-1"></i>' + label;
    }

    function getCaptureStatusUrl(requestId) {
        return captureStatusUrlTemplate.replace(
            "999999",
            String(requestId)
        );
    }

    async function waitForCaptureResult(requestId, messageElement) {
        const statusUrl = getCaptureStatusUrl(requestId);
        const deadline = Date.now() + 90000;

        while (Date.now() < deadline) {
            await new Promise(resolve => setTimeout(resolve, 1500));

            const response = await fetch(
                statusUrl + "?t=" + Date.now(),
                {
                    method: "GET",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json"
                    },
                    cache: "no-store"
                }
            );

            const data = await parseResponse(response);

            if (data.status === "completed") {
                return data;
            }

            if (data.status === "failed") {
                throw new Error(
                    data.message ||
                    "The fingerprint device reported a failure."
                );
            }

            if (data.status === "capturing") {
                setMessage(
                    messageElement,
                    "The device is capturing and uploading fingerprint data.",
                    "info"
                );
            } else if (data.status === "pending") {
                setMessage(
                    messageElement,
                    "Waiting for the fingerprint device to accept the request.",
                    "info"
                );
            }
        }

        throw new Error(
            "Timed out waiting for the fingerprint device. Check its power, Wi-Fi, and Django polling connection."
        );
    }

    async function captureFinger(finger) {
        const isLeft = finger === "left";
        const button = isLeft ? leftButton : rightButton;

        const status = document.getElementById(
            isLeft ? "leftFingerStatus" : "rightFingerStatus"
        );

        const message = document.getElementById(
            isLeft ? "leftCaptureMessage" : "rightCaptureMessage"
        );

        if (button.dataset.busy === "true") return;

        button.dataset.busy = "true";
        leftButton.disabled = true;
        rightButton.disabled = true;

        button.innerHTML =
            '<span class="spinner-border spinner-border-sm me-2"></span>' +
            "Sending Capture Request...";

        setStatus(status, "Waiting", "waiting");

        setMessage(
            message,
            `Sending the ${finger} fingerprint capture request...`,
            "info"
        );

        try {
            const formData = new FormData();
            formData.append("finger", finger);

            const response = await fetch(startCaptureUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json"
                },
                body: formData
            });

            const data = await parseResponse(response);

            if (!data.success || !data.request_id) {
                throw new Error(
                    data.error ||
                    data.message ||
                    "Django did not create the capture request."
                );
            }

            button.innerHTML =
                '<span class="spinner-border spinner-border-sm me-2"></span>' +
                "Waiting for Scanner...";

            setMessage(
                message,
                "Request created. Place the selected finger on the scanner when prompted.",
                "info"
            );

            const result = await waitForCaptureResult(
                data.request_id,
                message
            );

            setMessage(
                message,
                result.message ||
                "Capture finished. Refreshing saved biometric data...",
                "success"
            );

            window.location.reload();

        } catch (error) {
            console.error(`${finger} fingerprint error:`, error);

            setStatus(status, "Not Confirmed", "error");

            setMessage(
                message,
                error.message || "Fingerprint capture failed.",
                "error"
            );

            button.innerHTML = getFingerButtonLabel(finger);

        } finally {
            button.dataset.busy = "false";
            leftButton.disabled = false;
            rightButton.disabled = false;
        }
    }

    leftButton.addEventListener("click", function () {
        captureFinger("left");
    });

    rightButton.addEventListener("click", function () {
        captureFinger("right");
    });


});
