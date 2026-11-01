(() => {
    const form = document.getElementById("receiptForm");
    const update = () => {
        document.querySelectorAll("[data-value]").forEach(node => {
            const input = form.elements.namedItem(node.dataset.value);
            node.textContent = input.value.trim() || "________________________";
        });
    };
    form.addEventListener("input", update);
    form.addEventListener("change", update);
    document.getElementById("printReceipt").addEventListener("click", () => window.print());
    update();
})();
