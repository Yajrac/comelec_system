window.addEventListener("beforeprint", function () {
        document.title = document.getElementById("slipPrintConfig").dataset.printTitle;
    });
