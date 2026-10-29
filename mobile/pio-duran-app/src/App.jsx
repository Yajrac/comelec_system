import React, { useEffect } from "react";
import {
    BrowserRouter,
    Routes,
    Route,
} from "react-router-dom";

import Home from "./pages/Home";
import VerifyApplicant from "./pages/VerifyApplicant";
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

            startSyncManager();

        };


        initializeOfflineSystem();


        /*
        =====================================================
        CLEANUP
        =====================================================
        */

        return () => {

            stopSyncManager();

        };

    }, []);


    return (
        <BrowserRouter>

            <Routes>

                <Route
                    path="/"
                    element={<Home />}
                />

                <Route
                    path="/verify-applicant"
                    element={<VerifyApplicant />}
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

        </BrowserRouter>
    );
};


export default App;