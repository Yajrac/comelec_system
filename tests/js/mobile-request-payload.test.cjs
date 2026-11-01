const test = require('node:test');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const moduleUrl = pathToFileURL(path.resolve(__dirname, '../../mobile/pio-duran-app/src/services/requestPayload.js')).href;

global.FileReader = class {
    async readAsDataURL(file) {
        try {
            this.result = `data:${file.type};base64,${Buffer.from(await file.arrayBuffer()).toString('base64')}`;
            this.onload();
        } catch { this.onerror(); }
    }
};

test('photo and document survive JSON offline storage and multipart reconstruction', async () => {
    const { serializeRequestPayload, toRequestBody } = await import(moduleUrl);
    const original = { profile_details_provided: '1', suffix: 'Jr.', is_illiterate: true,
        is_indigenous: false, photo: new File([Uint8Array.from([0, 1, 255])], 'photo.png', { type: 'image/png' }),
        valid_id_document: new File(['%PDF-1.7 document'], 'id.pdf', { type: 'application/pdf' }) };
    const saved = JSON.parse(JSON.stringify(await serializeRequestPayload(original)));
    const body = toRequestBody(saved);
    assert.equal(body.get('photo').name, 'photo.png');
    assert.deepEqual([...new Uint8Array(await body.get('photo').arrayBuffer())], [0, 1, 255]);
    assert.equal(await body.get('valid_id_document').text(), '%PDF-1.7 document');
    assert.equal(body.get('is_illiterate'), 'on');
    assert.equal(body.has('is_indigenous'), false);
    assert.equal(body.get('suffix'), 'Jr.');
});

test('legacy JSON requests keep their existing format', async () => {
    const { toRequestBody } = await import(moduleUrl);
    const payload = { applicant_id: 1, reason: 'Correct my name' };
    assert.equal(toRequestBody(payload), payload);
});

test('profile submission without replacement files uses multipart and omits nulls', async () => {
    const { toRequestBody } = await import(moduleUrl);
    const body = toRequestBody({ profile_details_provided: '1', photo: null, valid_id_document: null, suffix: '' });
    assert.equal(body.get('profile_details_provided'), '1');
    assert.equal(body.get('suffix'), '');
    assert.equal(body.has('photo'), false);
    assert.equal(body.has('valid_id_document'), false);
});
