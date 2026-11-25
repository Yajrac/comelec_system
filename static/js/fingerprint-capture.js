document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const config = document.getElementById("csrfForm");
    if (!config) return;
    const startCaptureUrl = config.dataset.startCaptureUrl;
    const captureStatusUrlTemplate = config.dataset.captureStatusUrl;
    const cancelCaptureUrlTemplate = config.dataset.cancelCaptureUrl;

    // Active capture per finger, so the officer can cancel it while waiting.
    const activeCapture = { left: null, right: null };

    function createCancelButton(finger) {
        const captureButton = document.getElementById(
            finger === "left" ? "captureLeftFinger" : "captureRightFinger"
        );
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "btn btn-outline-danger bio-action mt-2";
        cancel.hidden = true;
        cancel.innerHTML = '<i class="bi bi-x-circle me-1" aria-hidden="true"></i>Cancel Capture';
        cancel.setAttribute("aria-label", `Cancel ${finger} thumbprint capture`);
        cancel.addEventListener("click", () => cancelCapture(finger));
        captureButton.insertAdjacentElement("afterend", cancel);
        return cancel;
    }

    const cancelButtons = {
        left: createCancelButton("left"),
        right: createCancelButton("right")
    };

    class CaptureCancelled extends Error {}

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
            ? `Recapture ${fingerName} Thumb`
            : `Capture ${fingerName} Thumb`;

        return '<i class="bi bi-fingerprint me-1"></i>' + label;
    }

    function getCaptureStatusUrl(requestId) {
        return captureStatusUrlTemplate.replace(
            "999999",
            String(requestId)
        );
    }

    async function cancelCapture(finger) {
        const active = activeCapture[finger];
        const cancel = cancelButtons[finger];
        if (!active || active.cancelling) return;
        active.cancelling = true;
        cancel.disabled = true;
        cancel.innerHTML =
            '<span class="spinner-border spinner-border-sm me-2"></span>Cancelling...';
        try {
            const response = await fetch(
                cancelCaptureUrlTemplate.replace("999999", String(active.requestId)),
                {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json"
                    }
                }
            );
            const data = await parseResponse(response);
            // A capture that finished just before the cancel arrived is kept.
            if (data.status === "cancelled") active.cancelled = true;
        } catch (error) {
            active.cancelling = false;
            cancel.disabled = false;
            cancel.innerHTML =
                '<i class="bi bi-x-circle me-1" aria-hidden="true"></i>Cancel Capture';
            const message = document.getElementById(
                finger === "left" ? "leftCaptureMessage" : "rightCaptureMessage"
            );
            setMessage(message, (error.message || "Unable to cancel.") + " Try again.", "error");
        }
    }

    async function waitForCaptureResult(requestId, messageElement, finger) {
        const statusUrl = getCaptureStatusUrl(requestId);
        const deadline = Date.now() + 90000;

        while (Date.now() < deadline) {
            await new Promise(resolve => setTimeout(resolve, 1500));

            if (activeCapture[finger]?.cancelled) {
                throw new CaptureCancelled();
            }

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

            if (activeCapture[finger]) activeCapture[finger].lastStatus = data.status;

            if (data.status === "completed") {
                return data;
            }

            if (data.status === "cancelled") {
                throw new CaptureCancelled();
            }

            if (data.status === "failed") {
                const failure = new Error(
                    data.message ||
                    "The fingerprint device reported a failure."
                );
                failure.canAcceptPartial = Boolean(data.can_accept_partial);
                throw failure;
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

        // Stop the scanner from picking up this request after the page gives up.
        await fetch(cancelCaptureUrlTemplate.replace("999999", String(requestId)), {
            method: "POST",
            headers: { "X-CSRFToken": getCsrfToken(), "X-Requested-With": "XMLHttpRequest" }
        }).catch(() => {});

        throw new Error(
            "Timed out waiting for the fingerprint device. Check its power, Wi-Fi, and Django polling connection."
        );
    }

    // After repeated partial thumbprints the officer may keep the next capture as it is.
    function showAcceptPartial(finger, messageElement) {
        let accept = document.getElementById(`${finger}AcceptPartial`);
        if (!accept) {
            accept = document.createElement("button");
            accept.type = "button";
            accept.id = `${finger}AcceptPartial`;
            accept.className = "btn btn-sm btn-outline-warning mt-2";
            accept.textContent = "Capture again and accept as is (officer)";
            accept.addEventListener("click", () => {
                if (!window.confirm("Accept the next capture even if it is partial? Use this only when a whole thumbprint cannot be taken (for example, an injured thumb).")) return;
                accept.remove();
                captureFinger(finger, true);
            });
            messageElement.insertAdjacentElement("afterend", accept);
        }
    }

    async function captureFinger(finger, acceptPartial = false) {
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
            `Sending the ${finger} thumbprint capture request...`,
            "info"
        );

        try {
            const formData = new FormData();
            formData.append("finger", finger);
            if (acceptPartial) formData.append("accept_partial", "1");

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

            activeCapture[finger] = { requestId: data.request_id };
            const cancel = cancelButtons[finger];
            cancel.disabled = false;
            cancel.innerHTML =
                '<i class="bi bi-x-circle me-1" aria-hidden="true"></i>Cancel Capture';
            cancel.hidden = false;

            setMessage(
                message,
                "Request created. Place the selected thumb flat on the scanner when prompted.",
                "info"
            );

            const result = await waitForCaptureResult(
                data.request_id,
                message,
                finger
            );

            setMessage(
                message,
                result.message ||
                "Capture finished. Refreshing saved biometric data...",
                "success"
            );

            window.location.reload();

        } catch (error) {
            if (error instanceof CaptureCancelled) {
                if (activeCapture[finger]?.lastStatus === "capturing") {
                    // The scanner may have uploaded before the cancel reached the server.
                    setStatus(status, "Check", "warning");
                    setMessage(
                        message,
                        "Capture cancelled while the scanner was reading. Refresh the page to confirm which thumbprint is saved.",
                        "info"
                    );
                    button.innerHTML = getFingerButtonLabel(finger);
                    return;
                }
                const saved = savedFingers[finger].image;
                setStatus(status, saved ? "Image Saved" : "Not Captured", saved ? "success" : "");
                setMessage(
                    message,
                    saved
                        ? "Capture cancelled. The previously saved thumbprint was kept."
                        : "Capture cancelled.",
                    "info"
                );
                button.innerHTML = getFingerButtonLabel(finger);
                return;
            }

            console.error(`${finger} fingerprint error:`, error);

            setStatus(status, "Not Confirmed", "error");

            setMessage(
                message,
                error.message || "Fingerprint capture failed.",
                "error"
            );
            if (error.canAcceptPartial) showAcceptPartial(finger, message);

            button.innerHTML = getFingerButtonLabel(finger);

        } finally {
            activeCapture[finger] = null;
            cancelButtons[finger].hidden = true;
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
