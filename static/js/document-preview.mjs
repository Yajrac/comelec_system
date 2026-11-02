const previews = document.querySelectorAll('[data-pdf-preview]');
if (previews.length) {
    try {
        const pdfjs = await import('../vendor/pdfjs/pdf.mjs');
        pdfjs.GlobalWorkerOptions.workerSrc = new URL('../vendor/pdfjs/pdf.worker.mjs', import.meta.url).href;
        for (const container of previews) renderPreview(container, pdfjs);
    } catch (error) {
        previews.forEach(showError);
    }
}

function showError(container) {
    container.replaceChildren();
    const message = document.createElement('p');
    message.className = 'submitted-pdf-status';
    message.textContent = 'Preview unavailable. Use View full document below.';
    container.append(message);
}

async function renderPreview(container, pdfjs) {
    let pdf;
    try {
        pdf = await pdfjs.getDocument(container.dataset.pdfPreview).promise;
        container.replaceChildren();
        // Render pages only as they approach the visible preview area.
        const observer = new IntersectionObserver(entries => {
            entries.forEach(async entry => {
                if (!entry.isIntersecting) return;
                const canvas = entry.target;
                observer.unobserve(canvas);
                try {
                    const page = await pdf.getPage(Number(canvas.dataset.page));
                    const base = page.getViewport({ scale: 1 });
                    const scale = Math.min(window.devicePixelRatio || 1, 2);
                    const viewport = page.getViewport({ scale: (canvas.clientWidth / base.width) * scale });
                    canvas.width = Math.ceil(viewport.width);
                    canvas.height = Math.ceil(viewport.height);
                    await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
                    page.cleanup();
                } catch (error) {
                    canvas.replaceWith(Object.assign(document.createElement('p'), { textContent: 'Page unavailable. Open the full document to view it.' }));
                }
            });
        }, { root: container, rootMargin: '180px' });
        const firstPage = await pdf.getPage(1);
        const viewport = firstPage.getViewport({ scale: 1 });
        for (let number = 1; number <= pdf.numPages; number++) {
            const canvas = document.createElement('canvas');
            canvas.dataset.page = number;
            canvas.style.aspectRatio = `${viewport.width} / ${viewport.height}`;
            canvas.setAttribute('role', 'img');
            canvas.setAttribute('aria-label', `Document page ${number} of ${pdf.numPages}`);
            container.append(canvas);
            observer.observe(canvas);
        }
        window.addEventListener('pagehide', event => {
            if (event.persisted) return;
            observer.disconnect();
            pdf.destroy();
        });
    } catch (error) {
        showError(container);
        await pdf?.destroy();
    }
}
