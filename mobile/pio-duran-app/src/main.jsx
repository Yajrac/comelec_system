import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

import { initOfflineDatabase } from "./services/offlineDatabase";

async function startApp() {
    try {
        await initOfflineDatabase();
    } catch (error) {
        console.error(
            "Offline database initialization failed:",
            error
        );
    }

    ReactDOM.createRoot(
        document.getElementById("root")
    ).render(
        <React.StrictMode>
            <App />
        </React.StrictMode>
    );
}

startApp();