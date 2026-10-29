import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
    submitWithOfflineSupport,
} from "../services/apiRequest";

import "./Reactivation.css";


function Reactivation() {

    const navigate = useNavigate();


    const [formData, setFormData] = useState({
        lastname: "",
        firstname: "",
        middlename: "",
        birthdate: "",
        reason: "",
    });


    const [submitting, setSubmitting] = useState(false);

    const [error, setError] = useState("");

    const [success, setSuccess] = useState("");

    const [requestId, setRequestId] = useState("");

    const [requestStatus, setRequestStatus] = useState("");

    const [isOfflineSubmission, setIsOfflineSubmission] =
        useState(false);


    // =========================================================
    // HANDLE INPUT
    // =========================================================

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

        setRequestId("");

        setRequestStatus("");

        setIsOfflineSubmission(false);
    };


    // =========================================================
    // RESET FORM
    // =========================================================

    const resetForm = () => {

        setFormData({
            lastname: "",
            firstname: "",
            middlename: "",
            birthdate: "",
            reason: "",
        });
    };


    // =========================================================
    // SUBMIT
    // =========================================================

    const handleSubmit = async (event) => {

        event.preventDefault();


        setError("");

        setSuccess("");

        setRequestId("");

        setRequestStatus("");

        setIsOfflineSubmission(false);


        // =====================================================
        // VALIDATION
        // =====================================================

        if (
            !formData.lastname.trim() ||
            !formData.firstname.trim() ||
            !formData.middlename.trim() ||
            !formData.birthdate ||
            !formData.reason.trim()
        ) {

            setError(
                "Please complete all required fields."
            );

            return;
        }


        setSubmitting(true);


        try {

            const payload = {

                lastname:
                    formData.lastname.trim(),

                firstname:
                    formData.firstname.trim(),

                middlename:
                    formData.middlename.trim(),

                birthdate:
                    formData.birthdate,

                reason:
                    formData.reason.trim(),
            };


            console.log(
                "Submitting reactivation request:",
                payload
            );


            // =================================================
            // OFFLINE-SUPPORTED SUBMISSION
            // =================================================

            const result =
                await submitWithOfflineSupport({

                    requestType:
                        "REACTIVATION",

                    endpoint:
                        "/api/applicant-reactivation-requests/",

                    payload,
                });


            console.log(
                "Reactivation request result:",
                result
            );


            // =================================================
            // OFFLINE
            // =================================================

            if (result.offline) {

                setIsOfflineSubmission(true);


                setSuccess(
                    "Your reactivation request has been saved on this device. It will automatically be submitted when your internet connection is restored."
                );


                setRequestId(
                    result.client_reference ||
                    ""
                );


                setRequestStatus(
                    "WAITING FOR INTERNET"
                );


                resetForm();


                return;
            }


            // =================================================
            // ONLINE
            // =================================================

            const responseData =
                result.data || {};


            if (
                responseData.success === false
            ) {

                setError(
                    responseData.error ||
                    responseData.message ||
                    "Unable to submit the reactivation request."
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


            // =================================================
            // SUCCESS
            // =================================================

            setSuccess(
                responseData.message ||
                "Your reactivation request has been submitted successfully and is now pending review."
            );


            setRequestId(
                responseData.request_id ||
                responseData.id ||
                result.client_reference ||
                ""
            );


            setRequestStatus(
                responseData.status ||
                "PENDING"
            );


            resetForm();


        } catch (err) {

            console.error(
                "Reactivation submission error:",
                err
            );


            const responseData =
                err.response?.data;


            if (responseData) {

                setError(
                    responseData.error ||
                    responseData.message ||
                    "Unable to submit the reactivation request."
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


            } else if (err.request) {

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


    // =========================================================
    // BACK
    // =========================================================

    const handleBack = () => {

        navigate("/");
    };


    return (

        <div className="verify-page">


            {/* =================================================
                HEADER
            ================================================= */}

            <header className="government-header">

                <div className="government-header-inner">

                    <div className="government-logo">

                        <img
                            src="/images/PIODURAN.png"
                            alt="Pio Duran Registration"
                        />

                    </div>


                    <div className="government-title">

                        <h1>
                            Pio Duran Registration Office
                        </h1>

                        <p>
                            Voter Registration Services
                        </p>

                    </div>

                </div>

            </header>


            {/* =================================================
                NAVIGATION
            ================================================= */}

            <nav className="main-navigation">

                <div className="main-navigation-inner">

                    <button
                        type="button"
                        onClick={() =>
                            navigate("/")
                        }
                    >
                        Home
                    </button>


                    <button
                        type="button"
                        onClick={() =>
                            navigate("/verify-applicant")
                        }
                    >
                        Verify Applicant
                    </button>


                    <button
                        type="button"
                        onClick={() =>
                            navigate("/new-registration")
                        }
                    >
                        New Registration
                    </button>


                    <button
                        type="button"
                        className="active"
                    >
                        Reactivation
                    </button>

                </div>

            </nav>


            {/* =================================================
                MAIN
            ================================================= */}

            <main className="verify-main">

                <div className="verify-container">


                    <div className="page-header">

                        <h2>
                            Reactivation Request
                        </h2>

                        <p>
                            Request the reactivation of your
                            inactive voter registration.
                        </p>

                    </div>


                    {/* =================================================
                        SUCCESS
                    ================================================= */}

                    {success && (

                        <div
                            className={
                                isOfflineSubmission
                                    ? "form-success offline-success"
                                    : "form-success"
                            }
                        >

                            <strong>
                                {isOfflineSubmission
                                    ? "Saved Offline"
                                    : "Request Submitted"
                                }
                            </strong>


                            <p>
                                {success}
                            </p>


                            {requestId && (

                                <p>

                                    Reference:
                                    {" "}

                                    <strong>
                                        {requestId}
                                    </strong>

                                </p>

                            )}


                            {requestStatus && (

                                <p>

                                    Status:
                                    {" "}

                                    <strong>
                                        {requestStatus}
                                    </strong>

                                </p>

                            )}


                            {isOfflineSubmission ? (

                                <p>
                                    Your request is stored on
                                    this device and will be
                                    automatically submitted to
                                    the registration server when
                                    your internet connection is
                                    restored.
                                </p>

                            ) : (

                                <p>
                                    Your request is now pending
                                    review by the registration
                                    office. Your registration
                                    will remain inactive until
                                    the request is reviewed and
                                    approved.
                                </p>

                            )}

                        </div>

                    )}


                    {/* =================================================
                        ERROR
                    ================================================= */}

                    {error && (

                        <div className="form-error">

                            <strong>
                                Unable to Submit
                            </strong>

                            <div>
                                {error}
                            </div>

                        </div>

                    )}


                    {/* =================================================
                        CARD
                    ================================================= */}

                    <div className="verify-card">

                        <div className="card-header-government">

                            <h3>
                                Reactivation Information
                            </h3>

                            <p>
                                Enter the information associated
                                with your inactive registration.
                            </p>

                        </div>


                        <div className="card-body-government">

                            <form
                                onSubmit={handleSubmit}
                            >


                                {/* =================================================
                                    PERSONAL INFORMATION
                                ================================================= */}

                                <div className="form-section">

                                    <h4 className="section-title">
                                        Personal Information
                                    </h4>


                                    <div className="form-grid">


                                        <div className="form-field">

                                            <label className="form-label">

                                                Last Name
                                                <span>*</span>

                                            </label>


                                            <input
                                                type="text"
                                                name="lastname"
                                                value={
                                                    formData.lastname
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                className="form-control"
                                                placeholder="Enter last name"
                                                autoComplete="family-name"
                                                disabled={
                                                    submitting
                                                }
                                                required
                                            />

                                        </div>


                                        <div className="form-field">

                                            <label className="form-label">

                                                First Name
                                                <span>*</span>

                                            </label>


                                            <input
                                                type="text"
                                                name="firstname"
                                                value={
                                                    formData.firstname
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                className="form-control"
                                                placeholder="Enter first name"
                                                autoComplete="given-name"
                                                disabled={
                                                    submitting
                                                }
                                                required
                                            />

                                        </div>


                                        <div className="form-field">

                                            <label className="form-label">

                                                Middle Name
                                                <span>*</span>

                                            </label>


                                            <input
                                                type="text"
                                                name="middlename"
                                                value={
                                                    formData.middlename
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                className="form-control"
                                                placeholder="Enter middle name"
                                                autoComplete="additional-name"
                                                disabled={
                                                    submitting
                                                }
                                                required
                                            />

                                        </div>


                                        <div className="form-field">

                                            <label className="form-label">

                                                Birthdate
                                                <span>*</span>

                                            </label>


                                            <input
                                                type="date"
                                                name="birthdate"
                                                value={
                                                    formData.birthdate
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                className="form-control"
                                                disabled={
                                                    submitting
                                                }
                                                required
                                            />

                                        </div>

                                    </div>

                                </div>


                                {/* =================================================
                                    REASON
                                ================================================= */}

                                <div className="form-section">

                                    <h4 className="section-title">
                                        Reason for Reactivation
                                    </h4>


                                    <div className="form-field">

                                        <label
                                            className="form-label"
                                            htmlFor="reason"
                                        >

                                            Reason
                                            <span>*</span>

                                        </label>


                                        <textarea
                                            id="reason"
                                            name="reason"
                                            value={
                                                formData.reason
                                            }
                                            onChange={
                                                handleChange
                                            }
                                            className="form-control"
                                            rows="6"
                                            placeholder="Please explain why you are requesting reactivation."
                                            disabled={
                                                submitting
                                            }
                                            required
                                        />

                                    </div>

                                </div>


                                {/* =================================================
                                    OFFLINE NOTICE
                                ================================================= */}

                                <div className="information-notice">

                                    <strong>
                                        Important Information
                                    </strong>


                                    <div>
                                        If your device has no
                                        internet connection, you
                                        can still submit this
                                        request.
                                    </div>


                                    <div>
                                        The request will be saved
                                        securely on this device
                                        until an internet connection
                                        becomes available.
                                    </div>


                                    <div>
                                        Once the connection is
                                        restored, the request will
                                        automatically be submitted
                                        to the registration server.
                                    </div>


                                    <div>
                                        Your inactive registration
                                        will not be reactivated
                                        immediately. The request
                                        must first be reviewed and
                                        approved by the registration
                                        office.
                                    </div>

                                </div>


                                {/* =================================================
                                    ACTIONS
                                ================================================= */}

                                <div className="form-actions">

                                    <button
                                        type="button"
                                        className="btn-secondary-government"
                                        onClick={handleBack}
                                        disabled={submitting}
                                    >
                                        Back
                                    </button>


                                    <button
                                        type="submit"
                                        className="btn-government"
                                        disabled={submitting}
                                    >

                                        {submitting
                                            ? "Submitting..."
                                            : "Submit Reactivation Request"
                                        }

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

            <footer className="site-footer">

                <div className="site-footer-inner">

                    <div className="footer-title">
                        Pio Duran Registration Office
                    </div>

                    <div className="footer-subtitle">
                        Voter Registration Services
                    </div>

                </div>

            </footer>

        </div>
    );
}


export default Reactivation;