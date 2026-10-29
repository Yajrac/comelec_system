import { Preferences } from "@capacitor/preferences";

const SYNC_QUEUE_KEY = "offline_sync_queue";


/*
=========================================================
INITIALIZE OFFLINE DATABASE
=========================================================
*/

export async function initOfflineDatabase() {
    try {
        const existingQueue =
            await getSyncQueue();

        if (!Array.isArray(existingQueue)) {
            await saveSyncQueue([]);
        }

        console.log(
            "Offline database initialized."
        );

        return true;
    } catch (error) {
        console.error(
            "Failed to initialize offline database:",
            error
        );

        return false;
    }
}


/*
=========================================================
GENERATE CLIENT REFERENCE
=========================================================
*/

export function generateClientReference(
    requestType
) {
    const prefix =
        String(requestType || "APPLICATION")
            .replace(/[^A-Z0-9]/gi, "")
            .toUpperCase();

    const timestamp = Date.now();

    const randomPart =
        Math.random()
            .toString(36)
            .substring(2, 10)
            .toUpperCase();

    return `${prefix}-${timestamp}-${randomPart}`;
}


/*
=========================================================
GET SYNC QUEUE
=========================================================
*/

export async function getSyncQueue() {
    try {
        const { value } =
            await Preferences.get({
                key: SYNC_QUEUE_KEY,
            });

        if (!value) {
            return [];
        }

        const parsed =
            JSON.parse(value);

        if (!Array.isArray(parsed)) {
            return [];
        }

        return parsed;
    } catch (error) {
        console.error(
            "Failed to read offline queue:",
            error
        );

        return [];
    }
}


/*
=========================================================
SAVE SYNC QUEUE
=========================================================
*/

async function saveSyncQueue(queue) {
    await Preferences.set({
        key: SYNC_QUEUE_KEY,
        value: JSON.stringify(queue),
    });
}


/*
=========================================================
ADD REQUEST TO QUEUE
=========================================================
*/

export async function addToSyncQueue({
    requestType,
    endpoint,
    payload,
    clientReference,
}) {
    try {
        const queue =
            await getSyncQueue();

        /*
        Prevent duplicate local requests.
        */

        const alreadyExists =
            queue.some(
                (item) =>
                    item.clientReference ===
                    clientReference
            );

        if (alreadyExists) {
            console.log(
                "Request already exists in offline queue:",
                clientReference
            );

            return;
        }

        const queueItem = {
            id: clientReference,

            requestType,

            endpoint,

            payload,

            clientReference,

            status: "WAITING",

            attempts: 0,

            createdAt:
                new Date().toISOString(),

            lastAttemptAt: null,

            lastError: null,
        };

        queue.push(queueItem);

        await saveSyncQueue(queue);

        console.log(
            `Saved offline request: ${requestType}`
        );

        console.log(
            `Reference: ${clientReference}`
        );

    } catch (error) {
        console.error(
            "Failed to save offline request:",
            error
        );

        throw error;
    }
}


/*
=========================================================
REMOVE REQUEST
=========================================================
*/

export async function removeFromSyncQueue(
    clientReference
) {
    const queue =
        await getSyncQueue();

    const updatedQueue =
        queue.filter(
            (item) =>
                item.clientReference !==
                clientReference
        );

    await saveSyncQueue(
        updatedQueue
    );
}


/*
=========================================================
UPDATE QUEUE ITEM
=========================================================
*/

export async function updateQueueItem(
    clientReference,
    updates
) {
    const queue =
        await getSyncQueue();

    const updatedQueue =
        queue.map((item) => {

            if (
                item.clientReference ===
                clientReference
            ) {
                return {
                    ...item,
                    ...updates,
                };
            }

            return item;
        });

    await saveSyncQueue(
        updatedQueue
    );
}


/*
=========================================================
CLEAR QUEUE
=========================================================
*/

export async function clearSyncQueue() {
    await Preferences.remove({
        key: SYNC_QUEUE_KEY,
    });
}


/*
=========================================================
GET PENDING COUNT
=========================================================
*/

export async function getPendingRequestCount() {
    const queue =
        await getSyncQueue();

    return queue.filter(
        (item) =>
            item.status === "WAITING" ||
            item.status === "RETRYING"
    ).length;
}


/*
=========================================================
GET FAILED COUNT
=========================================================
*/

export async function getFailedRequestCount() {
    const queue =
        await getSyncQueue();

    return queue.filter(
        (item) =>
            item.status === "FAILED"
    ).length;
}