import "./utils/inputValidation.js";
import "./input-validation.css";
import React, { useEffect } from "react";
import {
    BrowserRouter,
    Routes,
    Route,
    Navigate,
} from "react-router-dom";

import Home from "./pages/Home";
import OfflineApplications from "./pages/OfflineApplications";
import BottomNavigation from "./components/BottomNavigation";
import MobileAppHeader from "./components/MobileAppHeader";
import NewRegistration from "./pages/NewRegistration";
import UpdateInformation from "./pages/UpdateInformation";
import Transfer from "./pages/Transfer";
import Reactivation from "./pages/Reactivation";
import Reinstatement from "./pages/Reinstatement";
import RegistrationSuccessful from "./pages/RegistrationSuccessful";

import {
    initOfflineDatabase,
} from "./services/offlineDatabase";

import {
    startSyncManager,
    stopSyncManager,
} from "./services/syncManager";


const App = () => {

    useEffect(() => {
        let cancelled = false;

        /*
        =====================================================
        INITIALIZE OFFLINE DATABASE
        =====================================================
        */

        const initializeOfflineSystem = async () => {

            try {

                await initOfflineDatabase();

                console.log(
                    "Offline database initialized successfully."
                );

            } catch (error) {

                console.error(
                    "Failed to initialize offline database:",
                    error
                );
            }


            /*
            =================================================
            START AUTOMATIC SYNC
            =================================================
            */

            if (!cancelled) void startSyncManager();

        };


        initializeOfflineSystem();


        /*
        =====================================================
        CLEANUP
        =====================================================
        */

        return () => {
            cancelled = true;
            void stopSyncManager();

        };

    }, []);


    return (
        <BrowserRouter>
            <MobileAppHeader />

            <Routes>
                <Route path="/offline" element={<OfflineApplications />} />

                <Route
                    path="/"
                    element={<Home />}
                />

                <Route
                    path="/verify-applicant"
                    element={<Navigate to="/new-registration" replace />}
                />

                <Route
                    path="/new-registration"
                    element={<NewRegistration />}
                />

                <Route
                    path="/update-information"
                    element={<UpdateInformation />}
                />

                <Route
                    path="/transfer"
                    element={<Transfer />}
                />

                <Route
                    path="/reactivation"
                    element={<Reactivation />}
                />

                <Route
                    path="/reinstatement"
                    element={<Reinstatement />}
                />

                <Route
                    path="/registration-successful"
                    element={<RegistrationSuccessful />}
                />

            </Routes>
            <BottomNavigation />

        </BrowserRouter>
    );
};


export default App;
