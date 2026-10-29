import axios from "axios";

import {
    addToSyncQueue,
    generateClientReference,
} from "./offlineDatabase";

import {
    isOnline,
} from "./syncManager";


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
SUPPORTED APPLICATION TYPES
=========================================================
*/

export const APPLICATION_TYPES = {
    NEW_REGISTRATION:
        "NEW_REGISTRATION",

    UPDATE_INFORMATION:
        "UPDATE_INFORMATION",

    TRANSFER:
        "TRANSFER",

    REACTIVATION:
        "REACTIVATION",

    REINSTATEMENT:
        "REINSTATEMENT",
};


/*
=========================================================
APPLICATION ENDPOINTS
=========================================================
*/

export const APPLICATION_ENDPOINTS = {
    NEW_REGISTRATION:
        "/api/registrations/",

    UPDATE_INFORMATION:
        "/api/applicant-update-requests/",

    TRANSFER:
        "/api/applicant-transfer-requests/",

    REACTIVATION:
        "/api/applicant-reactivation-requests/",

    REINSTATEMENT:
        "/api/applicant-reinstatement-requests/",
};


/*
=========================================================
GET APPLICATION ENDPOINT
=========================================================
*/

export function getApplicationEndpoint(
    requestType
) {
    return (
        APPLICATION_ENDPOINTS[requestType] ||
        null
    );
}


/*
=========================================================
CHECK SUPPORTED APPLICATION
=========================================================
*/

export function isSupportedApplicationType(
    requestType
) {
    return Boolean(
        APPLICATION_ENDPOINTS[requestType]
    );
}


/*
=========================================================
SUBMIT WITH OFFLINE SUPPORT
=========================================================
*/

export async function submitWithOfflineSupport({
    requestType,
    endpoint,
    payload,
}) {
    /*
    Validate request type.
    */

    if (
        !isSupportedApplicationType(
            requestType
        )
    ) {
        throw new Error(
            `Unsupported application type: ${requestType}`
        );
    }


    /*
    Validate endpoint.
    */

    if (!endpoint) {
        throw new Error(
            "Application endpoint is required."
        );
    }


    /*
    Generate unique client reference.
    */

    const clientReference =
        generateClientReference(
            requestType
        );


    /*
    Add client reference to payload.
    */

    const requestPayload = {
        ...payload,

        client_reference:
            clientReference,
    };


    /*
    =====================================================
    ONLINE SUBMISSION
    =====================================================
    */

    if (isOnline()) {
        try {
            const response =
                await axios.post(
                    `${API_URL}${endpoint}`,
                    requestPayload,
                    {
                        timeout: 15000,

                        headers: {
                            "Content-Type":
                                "application/json",
                        },
                    }
                );


            /*
            Successful server response.
            */

            if (
                response.status >= 200 &&
                response.status < 300
            ) {
                return {
                    success: true,

                    offline: false,

                    synced: true,

                    requestType,

                    client_reference:
                        clientReference,

                    data:
                        response.data,
                };
            }
        } catch (error) {

            /*
            Server returned an HTTP error.

            Do NOT save validation/business
            errors to the offline queue.

            Examples:
            400
            404
            409
            422
            */

            if (error.response) {
                throw error;
            }


            /*
            No server response.

            This is most likely a network
            connection problem.

            Save the request locally.
            */

            console.log(
                "Network unavailable."
            );

            console.log(
                `Saving ${requestType} request locally.`
            );
        }
    }


    /*
    =====================================================
    OFFLINE QUEUE
    =====================================================
    */

    await addToSyncQueue({
        requestType,

        endpoint,

        payload: requestPayload,

        clientReference,
    });


    /*
    Return offline result.
    */

    return {
        success: true,

        offline: true,

        synced: false,

        requestType,

        client_reference:
            clientReference,

        data: null,
    };
}


/*
=========================================================
CONVENIENCE FUNCTIONS
=========================================================
*/

/*
NEW REGISTRATION
*/

export async function submitNewRegistration(
    payload
) {
    return submitWithOfflineSupport({
        requestType:
            APPLICATION_TYPES.NEW_REGISTRATION,

        endpoint:
            APPLICATION_ENDPOINTS.NEW_REGISTRATION,

        payload,
    });
}


/*
UPDATE INFORMATION
*/

export async function submitUpdateInformation(
    payload
) {
    return submitWithOfflineSupport({
        requestType:
            APPLICATION_TYPES.UPDATE_INFORMATION,

        endpoint:
            APPLICATION_ENDPOINTS.UPDATE_INFORMATION,

        payload,
    });
}


/*
TRANSFER
*/

export async function submitTransfer(
    payload
) {
    return submitWithOfflineSupport({
        requestType:
            APPLICATION_TYPES.TRANSFER,

        endpoint:
            APPLICATION_ENDPOINTS.TRANSFER,

        payload,
    });
}


/*
REACTIVATION
*/

export async function submitReactivation(
    payload
) {
    return submitWithOfflineSupport({
        requestType:
            APPLICATION_TYPES.REACTIVATION,

        endpoint:
            APPLICATION_ENDPOINTS.REACTIVATION,

        payload,
    });
}


/*
REINSTATEMENT
*/

export async function submitReinstatement(
    payload
) {
    return submitWithOfflineSupport({
        requestType:
            APPLICATION_TYPES.REINSTATEMENT,

        endpoint:
            APPLICATION_ENDPOINTS.REINSTATEMENT,

        payload,
    });
}