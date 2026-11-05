(() => {
    const photo = document.getElementById("photo");
    if (!photo) return;
    const preview = document.getElementById("photoPreview");
    const error = document.getElementById("photoError");
    const original = preview.getAttribute("src");
    const take = document.getElementById("takeSelfie");
    const takeLabel = document.getElementById("takeSelfieLabel");
    const native = document.getElementById("nativeSelfie");
    const panel = document.getElementById("selfieCamera");
    const video = document.getElementById("selfieVideo");
    const capture = document.getElementById("captureSelfie");
    const cancel = document.getElementById("cancelSelfie");
    const status = document.getElementById("cameraStatus");
    let stream;
    let session = 0;
    let url;
    photo.form?.addEventListener('offline:submitted', () => {
        stopCamera();
        if (url) URL.revokeObjectURL(url);
        url = null;
        photo.setCustomValidity('');
        error.textContent = '';
        status.textContent = '';
        preview.hidden = true;
        preview.removeAttribute('src');
    });

    function stopCamera() {
        session += 1;
        if (stream) stream.getTracks().forEach(track => track.stop());
        stream = null;
        video.srcObject = null;
        panel.hidden = true;
        capture.disabled = true;
        take.disabled = false;
    }

    function selectPhoto(file) {
        try {
            const transfer = new DataTransfer();
            transfer.items.add(file);
            photo.files = transfer.files;
            photo.dispatchEvent(new Event("change", { bubbles: true }));
            takeLabel.textContent = "Retake Selfie";
            status.textContent = "Photo selected. It will be saved when you submit the application.";
        } catch {
            status.textContent = "Your browser cannot attach a camera photo. Please use the photo upload field instead.";
        }
    }

    take.addEventListener("click", async () => {
        if (!window.isSecureContext) {
            status.textContent = "Live camera requires HTTPS or localhost. You can use the device camera picker or upload a photo instead.";
            native.click();
            return;
        }
        if (!navigator.mediaDevices?.getUserMedia) {
            status.textContent = "Use your device's camera picker, or upload a photo if a camera is unavailable.";
            native.click();
            return;
        }
        stopCamera();
        const current = session;
        panel.hidden = false;
        take.disabled = true;
        status.textContent = "Allow camera access to take a selfie.";
        try {
            const opened = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: { facingMode: { ideal: "user" }, width: { ideal: 1280 }, height: { ideal: 960 } }
            });
            if (current !== session) {
                opened.getTracks().forEach(track => track.stop());
                return;
            }
            stream = opened;
            video.srcObject = stream;
            await video.play();
            if (current !== session) return;
            capture.disabled = !video.videoWidth;
            status.textContent = "Position your face in the preview, then select Capture Photo.";
        } catch (failure) {
            if (current !== session) return;
            stopCamera();
            const messages = {
                NotAllowedError: "Camera access was blocked. Allow camera access in your browser, then try again, or upload a photo.",
                NotFoundError: "No camera was found. Connect a camera or upload a photo.",
                NotReadableError: "The camera is busy or unavailable. Close other camera apps and try again, or upload a photo."
            };
            status.textContent = messages[failure.name] || "Could not open the camera. Try again or upload a photo.";
        }
    });

    video.addEventListener("loadeddata", () => {
        if (stream) capture.disabled = !video.videoWidth;
    });

    capture.addEventListener("click", () => {
        if (!stream || !video.videoWidth || !video.videoHeight) return;
        const current = session;
        capture.disabled = true;
        const canvas = document.createElement("canvas");
        const scale = Math.min(1, 1280 / Math.max(video.videoWidth, video.videoHeight));
        canvas.width = Math.round(video.videoWidth * scale);
        canvas.height = Math.round(video.videoHeight * scale);
        const context = canvas.getContext("2d");
        if (!context) {
            capture.disabled = false;
            status.textContent = "Could not capture the photo. Please upload a photo instead.";
            return;
        }
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(blob => {
            if (current !== session) return;
            if (!blob) {
                capture.disabled = false;
                status.textContent = "Could not capture the photo. Please try again.";
                return;
            }
            stopCamera();
            const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
            selectPhoto(new File([blob], `${timestamp}.jpg`, { type: "image/jpeg" }));
            take.focus();
        }, "image/jpeg", 0.9);
    });

    cancel.addEventListener("click", () => {
        stopCamera();
        status.textContent = "Camera closed. Your selected photo has been kept.";
        take.focus();
    });

    native.addEventListener("change", () => {
        if (native.files[0]) selectPhoto(native.files[0]);
        native.value = "";
    });

    window.addEventListener("pagehide", stopCamera);
    document.addEventListener("visibilitychange", () => {
        if (document.hidden && (stream || !panel.hidden)) {
            stopCamera();
            status.textContent = "Camera closed. Select Take Selfie to open it again.";
        }
    });
    photo.form.addEventListener("submit", stopCamera);
    photo.addEventListener("change", () => {
        stopCamera();
        status.textContent = "";
        if (url) URL.revokeObjectURL(url);
        photo.setCustomValidity("");
        error.textContent = "";
        const file = photo.files[0];
        let message = "";
        if (file && !/\.(jpe?g|png)$/i.test(file.name)) message = "Upload a JPG or PNG photo.";
        else if (file && file.size > 5 * 1024 * 1024) message = "Photo must be 5 MB or smaller.";
        photo.setCustomValidity(message);
        error.textContent = message;
        preview.hidden = true;
        if (file && !message) {
            url = URL.createObjectURL(file);
            preview.src = url;
            preview.hidden = false;
        } else if (!file && original) {
            preview.src = original;
            preview.hidden = false;
        }
    });
    preview.addEventListener("error", () => {
        if (!photo.files.length) return;
        const message = "Upload a valid JPG or PNG image.";
        photo.setCustomValidity(message);
        error.textContent = message;
        preview.hidden = true;
    });
})();
