const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function setup({ secure = true, getUserMedia } = {}) {
    function element() {
        const events = {};
        return {
            hidden: false, disabled: false, files: [], textContent: '',
            addEventListener(type, fn) { events[type] = fn; },
            fire(type) { return events[type]?.({ type }); },
            dispatchEvent(event) { return this.fire(event.type); },
            setCustomValidity(value) { this.validationMessage = value; },
            getAttribute() { return null; },
            focus() {},
            click() { this.clicked = true; },
        };
    }
    const ids = Object.fromEntries(['photo', 'photoPreview', 'photoError', 'takeSelfie', 'takeSelfieLabel', 'nativeSelfie',
        'selfieCamera', 'selfieVideo', 'captureSelfie', 'cancelSelfie', 'cameraStatus'].map(id => [id, element()]));
    ids.selfieCamera.hidden = true;
    ids.photo.form = element();
    ids.selfieVideo.videoWidth = 1920;
    ids.selfieVideo.videoHeight = 1080;
    ids.selfieVideo.play = async () => {};
    const tracks = [{ stopped: false, stop() { this.stopped = true; } }];
    const stream = { getTracks: () => tracks };
    const window = Object.assign(element(), { isSecureContext: secure });
    const document = Object.assign(element(), {
        getElementById: id => ids[id],
        createElement: () => ({ getContext: () => ({ drawImage() {} }),
            toBlob: callback => callback({ size: 128 }) }),
    });
    const context = {
        window, document,
        navigator: { mediaDevices: { getUserMedia: getUserMedia || (async () => stream) } },
        Event: class { constructor(type) { this.type = type; } },
        File: class { constructor(parts, name, options) { this.name = name; this.type = options.type; this.size = 128; } },
        DataTransfer: class {
            constructor() { this.files = []; this.items = { add: file => this.files.push(file) }; }
        },
        URL: { createObjectURL: () => 'blob:selfie', revokeObjectURL() {} },
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../static/js/profile-fields.js'), 'utf8'), context);
    return { ids, tracks, stream, window, document };
}

test('captures a JPEG into the actual form file input and closes the camera', async () => {
    const { ids, tracks } = setup();
    await ids.takeSelfie.fire('click');
    assert.equal(ids.selfieCamera.hidden, false);
    assert.equal(ids.captureSelfie.disabled, false);
    ids.captureSelfie.fire('click');
    assert.match(ids.photo.files[0].name, /^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z\.jpg$/);
    assert.equal(ids.photo.files[0].type, 'image/jpeg');
    assert.equal(ids.photoPreview.src, 'blob:selfie');
    assert.equal(ids.selfieCamera.hidden, true);
    assert.equal(tracks[0].stopped, true);
    assert.equal(ids.takeSelfieLabel.textContent, 'Retake Selfie');
});

test('permission denial leaves the existing photo untouched and permits retry', async () => {
    const { ids } = setup({ getUserMedia: async () => { throw { name: 'NotAllowedError' }; } });
    const previous = { name: 'previous.png' };
    ids.photo.files = [previous];
    await ids.takeSelfie.fire('click');
    assert.match(ids.cameraStatus.textContent, /blocked/);
    assert.equal(ids.photo.files[0], previous);
    assert.equal(ids.takeSelfie.disabled, false);
    assert.equal(ids.selfieCamera.hidden, true);
});

test('cancel during permission prompt stops a stream that arrives later', async () => {
    let resolveCamera;
    const { ids, stream, tracks } = setup({ getUserMedia: () => new Promise(resolve => { resolveCamera = resolve; }) });
    const pending = ids.takeSelfie.fire('click');
    ids.cancelSelfie.fire('click');
    resolveCamera(stream);
    await pending;
    assert.equal(tracks[0].stopped, true);
    assert.equal(ids.selfieCamera.hidden, true);
    assert.equal(ids.selfieVideo.srcObject, null);
});

test('insecure origin uses the device picker with an explanation', async () => {
    const { ids } = setup({ secure: false });
    await ids.takeSelfie.fire('click');
    assert.equal(ids.nativeSelfie.clicked, true);
    assert.match(ids.cameraStatus.textContent, /HTTPS or localhost/);
    ids.nativeSelfie.files = [{ name: 'mobile.jpg', size: 256 }];
    ids.nativeSelfie.fire('change');
    assert.equal(ids.photo.files[0].name, 'mobile.jpg');
});

test('leaving the page or submitting closes the active camera', async () => {
    for (const event of ['pagehide', 'submit', 'visibilitychange']) {
        const { ids, tracks, window, document } = setup();
        await ids.takeSelfie.fire('click');
        if (event === 'pagehide') window.fire(event);
        else if (event === 'submit') ids.photo.form.fire(event);
        else { document.hidden = true; document.fire(event); }
        assert.equal(tracks[0].stopped, true);
        assert.equal(ids.selfieCamera.hidden, true);
    }
});
