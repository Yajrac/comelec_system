import axios from "axios";
import { Network } from "@capacitor/network";

import {
    getSyncQueue,
    removeFromSyncQueue,
    updateQueueItem,
} from "./offlineDatabase";


/*
=========================================================
API BASE URL
=========================================================
*/

const API_URL =
    import.meta.env.VITE_API_URL ||
    "https://pio-duran-online-registration.onrender.com";


/*
=========================================================
SYNC STATE
=========================================================
*/

let onlineStatus = true;

let isSyncing = false;

let syncStarted = false;

let networkListener = null;


/*
=========================================================
CHECK ONLINE STATUS
=========================================================
*/

export function isOnline() {
    return onlineStatus;
}


/*
=========================================================
REFRESH NETWORK STATUS
=========================================================
*/

async function refreshNetworkStatus() {
    try {
        const status =
            await Network.getStatus();

        onlineStatus =
            Boolean(status.connected);

        return onlineStatus;

    } catch (error) {

        /*
        Browser fallback.
        */

        onlineStatus =
            navigator.onLine;

        return onlineStatus;
    }
}


/*
=========================================================
SYNC ONE REQUEST
=========================================================
*/

async function syncRequest(item) {

    if (!item) {
        return;
    }


    /*
    Mark request as retrying.
    */

    await updateQueueItem(
        item.clientReference,
        {
            status: "RETRYING",

            attempts:
                Number(item.attempts || 0) + 1,

            lastAttemptAt:
                new Date().toISOString(),

            lastError: null,
        }
    );


    try {

        console.log(
            `Syncing ${item.requestType}: ${item.clientReference}`
        );


        const response =
            await axios.post(
                `${API_URL}${item.endpoint}`,

                {
                    ...item.payload,

                    client_reference:
                        item.clientReference,
                },

                {
                    timeout: 15000,

                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                }
            );


        /*
        Successful submission.
        */

        if (
            response.status >= 200 &&
            response.status < 300
        ) {

            await removeFromSyncQueue(
                item.clientReference
            );


            console.log(
                `Successfully synced: ${item.requestType}`
            );


            return {
                success: true,

                requestType:
                    item.requestType,

                clientReference:
                    item.clientReference,

                data:
                    response.data,
            };
        }

    } catch (error) {

        /*
        =================================================
        SERVER ERROR
        =================================================
        */

        if (error.response) {

            const status =
                error.response.status;

            const responseData =
                error.response.data || {};


            /*
            Validation/business errors.

            Do not retry these forever.
            */

            if (
                status === 400 ||
                status === 404 ||
                status === 409 ||
                status === 422
            ) {

                const serverError =
                    responseData.error ||
                    responseData.message ||
                    `Server rejected the request (${status}).`;


                await updateQueueItem(
                    item.clientReference,
                    {
                        status: "FAILED",

                        lastError:
                            serverError,

                        lastAttemptAt:
                            new Date().toISOString(),
                    }
                );


                console.error(
                    `Offline request failed: ${item.requestType}`
                );

                console.error(
                    serverError
                );


                return {
                    success: false,

                    failed: true,

                    requestType:
                        item.requestType,

                    clientReference:
                        item.clientReference,

                    error:
                        serverError,
                };
            }


            /*
            Other server errors remain
            in the queue for retry.
            */

            await updateQueueItem(
                item.clientReference,
                {
                    status: "WAITING",

                    lastError:
                        responseData.error ||
                        responseData.message ||
                        `Server error: ${status}`,

                    lastAttemptAt:
                        new Date().toISOString(),
                }
            );


            return {
                success: false,

                retry: true,

                requestType:
                    item.requestType,

                clientReference:
                    item.clientReference,
            };
        }


        /*
        =================================================
        NETWORK ERROR
        =================================================
        */

        await updateQueueItem(
            item.clientReference,
            {
                status: "WAITING",

                lastError:
                    "Internet connection unavailable.",

                lastAttemptAt:
                    new Date().toISOString(),
            }
        );


        onlineStatus = false;


        return {
            success: false,

            retry: true,

            networkError: true,

            requestType:
                item.requestType,

            clientReference:
                item.clientReference,
        };
    }


    return {
        success: false,

        retry: true,

        requestType:
            item.requestType,

        clientReference:
            item.clientReference,
    };
}


/*
=========================================================
SYNC ALL PENDING REQUESTS
=========================================================
*/

export async function syncPendingRequests() {

    /*
    Prevent simultaneous synchronization.
    */

    if (isSyncing) {
        return;
    }


    /*
    Check internet connection.
    */

    const connected =
        await refreshNetworkStatus();


    if (!connected) {

        console.log(
            "Offline. Synchronization skipped."
        );

        return;
    }


    isSyncing = true;


    try {

        const queue =
            await getSyncQueue();


        /*
        Get only requests waiting
        for synchronization.
        */

        const pendingRequests =
            queue.filter(
                (item) =>
                    item.status === "WAITING" ||
                    item.status === "RETRYING"
            );


        if (
            pendingRequests.length === 0
        ) {

            console.log(
                "No offline requests to synchronize."
            );

            return;
        }


        console.log(
            `Found ${pendingRequests.length} pending request(s).`
        );


        /*
        Process one request at a time.
        */

        for (
            const item of pendingRequests
        ) {

            const stillOnline =
                await refreshNetworkStatus();


            if (!stillOnline) {

                console.log(
                    "Internet connection lost during synchronization."
                );

                break;
            }


            const result =
                await syncRequest(item);


            if (
                result &&
                result.networkError
            ) {

                break;
            }
        }

    } catch (error) {

        console.error(
            "Synchronization error:",
            error
        );

    } finally {

        isSyncing = false;
    }
}


/*
=========================================================
START SYNC MANAGER
=========================================================
*/

export async function startSyncManager() {

    /*
    Prevent duplicate initialization.

    This is especially important because
    React StrictMode can execute effects
    more than once during development.
    */

    if (syncStarted) {

        console.log(
            "Sync manager already started."
        );

        return;
    }


    syncStarted = true;


    /*
    Get current network state.
    */

    await refreshNetworkStatus();


    console.log(
        `Initial network status: ${
            onlineStatus
                ? "ONLINE"
                : "OFFLINE"
        }`
    );


    /*
    If online, immediately synchronize
    pending requests.
    */

    if (onlineStatus) {

        syncPendingRequests();
    }


    /*
    Listen for Capacitor network changes.
    */

    try {

        networkListener =
            await Network.addListener(
                "networkStatusChange",
                (status) => {

                    onlineStatus =
                        Boolean(
                            status.connected
                        );


                    console.log(
                        `Network status changed: ${
                            onlineStatus
                                ? "ONLINE"
                                : "OFFLINE"
                        }`
                    );


                    /*
                    Internet has returned.
                    */

                    if (onlineStatus) {

                        syncPendingRequests();
                    }
                }
            );


    } catch (error) {

        console.error(
            "Capacitor network listener failed:",
            error
        );


        /*
        Browser fallback.
        */

        window.addEventListener(
            "online",
            handleBrowserOnline
        );


        window.addEventListener(
            "offline",
            handleBrowserOffline
        );
    }
}


/*
=========================================================
BROWSER ONLINE HANDLER
=========================================================
*/

function handleBrowserOnline() {

    onlineStatus = true;

    console.log(
        "Browser network: ONLINE"
    );

    syncPendingRequests();
}


/*
=========================================================
BROWSER OFFLINE HANDLER
=========================================================
*/

function handleBrowserOffline() {

    onlineStatus = false;

    console.log(
        "Browser network: OFFLINE"
    );
}


/*
=========================================================
ALIAS
=========================================================
*/

export const initSyncManager =
    startSyncManager;


/*
=========================================================
STOP SYNC MANAGER
=========================================================
*/

export async function stopSyncManager() {

    if (networkListener) {

        await networkListener.remove();

        networkListener = null;
    }


    window.removeEventListener(
        "online",
        handleBrowserOnline
    );


    window.removeEventListener(
        "offline",
        handleBrowserOffline
    );


    syncStarted = false;

    console.log(
        "Sync manager stopped."
    );
}