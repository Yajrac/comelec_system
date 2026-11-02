import { API_BASE_URL } from "../services/apiConfig";
import RequestProfileFields from "../components/RequestProfileFields";
import { initialRequestProfile, requestProfileError } from "../utils/requestProfile";
import ReferenceLookup from "../components/ReferenceLookup";
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

import {
    submitWithOfflineSupport,
} from "../services/apiRequest";

import "./Transfer.css";





const Transfer = ({ applicant }) => {

    const navigate = useNavigate();


    /*
    =========================================================
    FORM DATA
    =========================================================
    */

    const [profile, setProfile] = useState(() => initialRequestProfile(applicant));

    const [formData, setFormData] = useState({

        lastname: applicant.lastname || "",

        firstname: applicant.firstname || "",

        middlename: applicant.middlename || "",

        birthdate: applicant.birthdate || "",

        current_brgy: applicant.brgy || "",

        new_brgy: "",

        current_municipality: applicant.municipality || "Pio Duran",

        current_province: applicant.province || "Albay",

        new_municipality: "Pio Duran",

        new_province: "Albay",

        reason: "",
    });


    /*
    =========================================================
    BARANGAYS
    =========================================================
    */

    const [barangays, setBarangays] = useState([]);

    const [loadingBarangays, setLoadingBarangays] =
        useState(true);


    /*
    =========================================================
    SUBMISSION
    =========================================================
    */

    const [submitting, setSubmitting] =
        useState(false);


    /*
    =========================================================
    MESSAGES
    =========================================================
    */

    const [error, setError] =
        useState("");

    const [success, setSuccess] =
        useState("");

    const [requestId, setRequestId] =
        useState(null);

    const [requestStatus, setRequestStatus] =
        useState("");


    /*
    =========================================================
    LOAD BARANGAYS
    =========================================================
    */

    useEffect(() => {

        const loadBarangays = async () => {

            try {

                setLoadingBarangays(true);


                const response =
                    await axios.get(
                        `${API_BASE_URL}/api/barangays/`
                    );


                if (
                    response.data &&
                    Array.isArray(
                        response.data.barangays
                    )
                ) {

                    setBarangays(
                        response.data.barangays
                    );

                } else if (
                    response.data &&
                    Array.isArray(
                        response.data.results
                    )
                ) {

                    setBarangays(
                        response.data.results
                    );

                } else if (
                    Array.isArray(
                        response.data
                    )
                ) {

                    setBarangays(
                        response.data
                    );

                } else {

                    setBarangays([]);
                }

            } catch (err) {

                console.error(
                    "Failed to load barangays:",
                    err
                );


                setBarangays([]);


                setError(
                    "Unable to load the barangay list. Please check your internet connection and try again."
                );

            } finally {

                setLoadingBarangays(false);
            }
        };


        loadBarangays();

    }, []);


    /*
    =========================================================
    HANDLE INPUT
    =========================================================
    */

    const handleChange = (event) => {

        const {
            name,
            value,
        } = event.target;


        setFormData((previous) => ({

            ...previous,

            [name]: value,

        }));


        setError("");

        setSuccess("");

        setRequestId(null);

        setRequestStatus("");
    };


    /*
    =========================================================
    RESET FORM
    =========================================================
    */

    const resetForm = () => {
        setProfile(initialRequestProfile(applicant));

        setFormData({

            lastname: applicant.lastname || "",

            firstname: applicant.firstname || "",

            middlename: applicant.middlename || "",

            birthdate: applicant.birthdate || "",

            current_brgy: applicant.brgy || "",

            new_brgy: "",

            current_municipality:
                "Pio Duran",

            current_province:
                "Albay",

            new_municipality:
                "Pio Duran",

            new_province:
                "Albay",

            reason: "",
        });
    };


    /*
    =========================================================
    SUBMIT TRANSFER REQUEST
    =========================================================
    */

    const handleSubmit = async (event) => {

        event.preventDefault();
        const profileError = requestProfileError(profile, applicant);
        if (profileError) { setError(profileError); return; }



        setError("");

        setSuccess("");

        setRequestId(null);

        setRequestStatus("");


        /*
        =====================================================
        CLIENT VALIDATION
        =====================================================
        */

        if (
            !formData.lastname.trim() ||
            !formData.firstname.trim() ||
            !formData.birthdate ||
            !formData.current_brgy ||
            !formData.new_brgy
        ) {

            setError(
                "Please complete all required fields."
            );

            return;
        }


        /*
        =====================================================
        BARANGAY VALIDATION
        =====================================================
        */

        if (
            formData.current_brgy ===
            formData.new_brgy
        ) {

            setError(
                "The new barangay must be different from your current barangay."
            );

            return;
        }


        /*
        =====================================================
        SUBMIT
        =====================================================
        */

        try {

            setSubmitting(true);


            /*
            =================================================
            PREPARE PAYLOAD
            =================================================
            */

            const payload = {
            ...profile,
                registration_reference: applicant.registration_reference,

                lastname:
                    formData.lastname.trim(),

                firstname:
                    formData.firstname.trim(),

                middlename:
                    formData.middlename.trim(),

                birthdate:
                    formData.birthdate,

                current_brgy:
                    formData.current_brgy
                        ? Number(
                            formData.current_brgy
                        )
                        : null,

                new_brgy:
                    formData.new_brgy
                        ? Number(
                            formData.new_brgy
                        )
                        : null,

                current_municipality:
                    formData.current_municipality.trim(),

                current_province:
                    formData.current_province.trim(),

                new_municipality:
                    formData.new_municipality.trim(),

                new_province:
                    formData.new_province.trim(),

                reason:
                    formData.reason.trim(),
            };


            console.log(
                "Submitting transfer request:",
                payload
            );


            /*
            =================================================
            OFFLINE-SUPPORTED SUBMISSION
            =================================================

            ONLINE:
                Request is immediately sent to Django.

            OFFLINE:
                Request is saved locally on the device.

            INTERNET RESTORED:
                syncManager automatically sends it.
            =================================================
            */

            const result =
                await submitWithOfflineSupport({

                    requestType:
                        "TRANSFER",

                    endpoint:
                        "/api/applicant-transfer-requests/",

                    payload,
                });


            console.log(
                "Transfer request result:",
                result
            );


            /*
            =================================================
            OFFLINE
            =================================================
            */

            if (
                result.offline
            ) {

                setSuccess(
                    "Your transfer request has been saved on this device. It will automatically be submitted when your internet connection is restored."
                );


                setRequestId(
                    result.client_reference ||
                    ""
                );


                setRequestStatus(
                    "WAITING FOR INTERNET"
                );


                /*
                =============================================
                CLEAR FORM
                =============================================
                */

                resetForm();


                return;
            }


            /*
            =================================================
            ONLINE SUCCESS
            =================================================
            */

            const responseData =
                result.data || {};


            if (
                responseData.success === false
            ) {

                setError(
                    responseData.error ||
                    responseData.message ||
                    "Unable to submit the transfer request."
                );


                if (
                    responseData.request_id
                ) {

                    setRequestId(
                        responseData.request_id
                    );
                }


                if (
                    responseData.status
                ) {

                    setRequestStatus(
                        responseData.status
                    );
                }


                return;
            }


            /*
            =================================================
            SUCCESS MESSAGE
            =================================================
            */

            setSuccess(
                responseData.message ||
                "Your transfer request has been submitted successfully and is now pending review."
            );


            /*
            =================================================
            REQUEST ID
            =================================================
            */

            setRequestId(
                responseData.request_id ||
                responseData.id ||
                result.client_reference ||
                ""
            );


            /*
            =================================================
            REQUEST STATUS
            =================================================
            */

            setRequestStatus(
                responseData.status ||
                "PENDING"
            );


            /*
            =================================================
            CLEAR FORM
            =================================================
            */

            resetForm();


        } catch (err) {

            console.error(
                "Transfer request error:",
                err
            );


            /*
            =================================================
            DJANGO ERROR
            =================================================
            */

            if (
                err.response?.data
            ) {

                const responseData =
                    err.response.data;


                setError(
                    responseData.error ||
                    responseData.message ||
                    "Unable to submit the transfer request."
                );


                if (
                    responseData.request_id
                ) {

                    setRequestId(
                        responseData.request_id
                    );
                }


                if (
                    responseData.status
                ) {

                    setRequestStatus(
                        responseData.status
                    );
                }


            } else if (
                err.request
            ) {

                setError(
                    "Unable to connect to the registration server. Please try again."
                );

            } else {

                setError(
                    "An unexpected error occurred. Please try again."
                );
            }

        } finally {

            setSubmitting(false);
        }
    };


    /*
    =========================================================
    RENDER
    =========================================================
    */

    return (

        <div className="verify-page">


            {/* =================================================
                HEADER
            ================================================= */}




            {/* =================================================
                NAVIGATION
            ================================================= */}




            {/* =================================================
                MAIN
            ================================================= */}

            <main className="verify-main">

                <div className="verify-container">


                    {/* =================================================
                        PAGE HEADER
                    ================================================= */}

                    <div className="page-header">

                        <h1>
                            Transfer
                        </h1>


                        <p>

                            Request the transfer of your existing
                            registration to another barangay or
                            locality.

                        </p>

                    </div>


                    {/* =================================================
                        CARD
                    ================================================= */}

                    <div className="verify-card">


                        {/* =================================================
                            CARD HEADER
                        ================================================= */}

                        <div className="card-header-government">

                            <h2>
                                Transfer Request
                            </h2>


                            <p>

                                Enter your applicant information
                                and provide the details of the
                                requested transfer.

                            </p>

                        </div>


                        {/* =================================================
                            CARD BODY
                        ================================================= */}

                        <div className="card-body-government">


                            {/* =================================================
                                ERROR
                            ================================================= */}

                            {error && (

                                <div className="form-error">

                                    {error}

                                </div>

                            )}


                            {/* =================================================
                                SUCCESS
                            ================================================= */}

                            {success && (

                                <div className="form-success">


                                    <strong>

                                        Transfer Request

                                    </strong>


                                    <p>

                                        {success}

                                    </p>


                                    {requestId && (

                                        <p>

                                            Reference:

                                            <strong>

                                                {" "}

                                                #{requestId}

                                            </strong>

                                        </p>

                                    )}


                                    {requestStatus && (

                                        <p>

                                            Status:

                                            <strong>

                                                {" "}

                                                {requestStatus}

                                            </strong>

                                        </p>

                                    )}


                                    <p>

                                        Your existing registration
                                        record has not been changed
                                        yet. The requested transfer
                                        will only be applied after
                                        review and approval by the
                                        registration office.

                                    </p>


                                    {requestStatus ===
                                        "WAITING FOR INTERNET" && (

                                        <p>

                                            Please keep this application
                                            installed on your device.
                                            The request will remain
                                            stored locally until an
                                            internet connection becomes
                                            available.

                                        </p>

                                    )}

                                </div>

                            )}


                            {/* =================================================
                                FORM
                            ================================================= */}

                            <form
                                onSubmit={
                                    handleSubmit
                                }
                            >
<RequestProfileFields profile={profile} setProfile={setProfile} applicant={applicant} />



                                {/* =================================================
                                    APPLICANT INFORMATION
                                ================================================= */}




                                {/* =================================================
                                    CURRENT ADDRESS
                                ================================================= */}

                                <section className="form-section">

                                    <h3 className="section-title">

                                        Current Address

                                    </h3>


                                    <div className="form-grid">


                                        {/* CURRENT BARANGAY */}

                                        <div className="form-field full-width">

                                            <label className="form-label">

                                                Current Barangay

                                            </label>


                                            <select
                                                name="current_brgy"
                                                className="form-control"
                                                value={
                                                    formData.current_brgy
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                disabled
                                                required
                                            >


                                                <option value="">

                                                    {loadingBarangays
                                                        ? "Loading Barangays..."
                                                        : "Select Current Barangay"
                                                    }

                                                </option>


                                                {barangays.map(
                                                    (barangay) => (

                                                        <option
                                                            key={
                                                                barangay.id
                                                            }
                                                            value={
                                                                barangay.id
                                                            }
                                                        >

                                                            {
                                                                barangay.name
                                                            }

                                                        </option>

                                                    )
                                                )}

                                            </select>

                                        </div>


                                        {/* MUNICIPALITY */}

                                        <div className="form-field">

                                            <label className="form-label">

                                                Municipality

                                            </label>


                                            <input
                                                className="form-control" readOnly
                                                name="current_municipality"
                                                value={
                                                    formData.current_municipality
                                                }
                                                readOnly
                                            />

                                        </div>


                                        {/* PROVINCE */}

                                        <div className="form-field">

                                            <label className="form-label">

                                                Province

                                            </label>


                                            <input
                                                className="form-control" readOnly
                                                name="current_province"
                                                value={
                                                    formData.current_province
                                                }
                                                readOnly
                                            />

                                        </div>

                                    </div>

                                </section>


                                {/* =================================================
                                    NEW ADDRESS
                                ================================================= */}

                                <section className="form-section">

                                    <h3 className="section-title">

                                        New Address

                                    </h3>


                                    <div className="form-grid">


                                        {/* NEW BARANGAY */}

                                        <div className="form-field full-width">

                                            <label className="form-label">

                                                New Barangay

                                            </label>


                                            <select
                                                name="new_brgy"
                                                className="form-control"
                                                value={
                                                    formData.new_brgy
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                disabled={
                                                    loadingBarangays
                                                }
                                                required
                                            >


                                                <option value="">

                                                    {loadingBarangays
                                                        ? "Loading Barangays..."
                                                        : "Select New Barangay"
                                                    }

                                                </option>


                                                {barangays.map(
                                                    (barangay) => (

                                                        <option
                                                            key={
                                                                barangay.id
                                                            }
                                                            value={
                                                                barangay.id
                                                            }
                                                        >

                                                            {
                                                                barangay.name
                                                            }

                                                        </option>

                                                    )
                                                )}

                                            </select>

                                        </div>


                                        {/* MUNICIPALITY */}

                                        <div className="form-field">

                                            <label className="form-label">

                                                Municipality

                                            </label>


                                            <input
                                                className="form-control"
                                                name="new_municipality"
                                                value={
                                                    formData.new_municipality
                                                }
                                                readOnly
                                            />

                                        </div>


                                        {/* PROVINCE */}

                                        <div className="form-field">

                                            <label className="form-label">

                                                Province

                                            </label>


                                            <input
                                                className="form-control"
                                                name="new_province"
                                                value={
                                                    formData.new_province
                                                }
                                                readOnly
                                            />

                                        </div>

                                    </div>

                                </section>


                                {/* =================================================
                                    REASON
                                ================================================= */}

                                <section className="form-section">

                                    <h3 className="section-title">

                                        Reason for Transfer

                                    </h3>


                                    <div className="form-field">

                                        <label
                                            className="form-label"
                                            htmlFor="reason"
                                        >

                                            Reason

                                        </label>


                                        <textarea
                                            id="reason"
                                            name="reason" minLength={5} maxLength={2000}
                                            rows="5"
                                            className="form-control"
                                            value={
                                                formData.reason
                                            }
                                            onChange={
                                                handleChange
                                            }
                                            placeholder="Explain the reason for the transfer"
                                        />

                                    </div>

                                </section>


                                {/* =================================================
                                    OFFLINE NOTICE
                                ================================================= */}

                                <div className="information-notice">

                                    <strong>
                                        Important
                                    </strong>


                                    <div>

                                        If your device is temporarily
                                        offline, your transfer request
                                        can still be saved on this device.

                                    </div>


                                    <div>

                                        Once your internet connection
                                        is restored, the request will
                                        automatically be submitted to
                                        the registration server.

                                    </div>


                                    <div>

                                        Your existing registration record
                                        will not be changed immediately.
                                        The transfer request must first
                                        be reviewed and approved by the
                                        registration office.

                                    </div>

                                </div>


                                {/* =================================================
                                    ACTIONS
                                ================================================= */}

                                <RequestProfileFields part="documents" profile={profile} setProfile={setProfile} applicant={applicant} />
<div className="form-actions">


                                    <button
                                        type="submit"
                                        className="btn-government"
                                        disabled={
                                            submitting ||
                                            loadingBarangays
                                        }
                                    >

                                        {submitting
                                            ? "Submitting..."
                                            : "Submit Transfer Request"
                                        }

                                    </button>


                                    <button
                                        type="button"
                                        className="btn-secondary-government"
                                        onClick={() =>
                                            navigate("/")
                                        }
                                        disabled={
                                            submitting
                                        }
                                    >

                                        Back to Home

                                    </button>

                                </div>


                            </form>

                        </div>

                    </div>

                </div>

            </main>


            {/* =================================================
                FOOTER
            ================================================= */}


        </div>
    );
};


export default function TransferScreen() {
    return <ReferenceLookup type="TRANSFER">{applicant => <Transfer applicant={applicant} />}</ReferenceLookup>;
}
