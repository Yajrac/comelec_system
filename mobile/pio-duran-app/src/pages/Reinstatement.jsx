import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
    submitWithOfflineSupport,
} from "../services/apiRequest";

import "./Reinstatement.css";

const Reinstatement = () => {
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

        // =====================================================
        // CLIENT VALIDATION
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

            const result =
                await submitWithOfflineSupport({
                    requestType:
                        "REINSTATEMENT",

                    endpoint:
                        "/api/applicant-reinstatement-requests/",

                    payload,
                });

            console.log(
                "Reinstatement request result:",
                result
            );

            // =================================================
            // OFFLINE
            // =================================================

            if (result.offline) {
                setSuccess(
                    "Your reinstatement request has been saved on this device. It will automatically be submitted when your internet connection is restored."
                );

                setRequestId(
                    result.client_reference || ""
                );

                setRequestStatus(
                    "WAITING FOR INTERNET"
                );

                resetForm();

                return;
            }

            // =================================================
            // ONLINE SUCCESS
            // =================================================

            const responseData =
                result.data || {};

            if (
                responseData.success === false
            ) {
                setError(
                    responseData.error ||
                    responseData.message ||
                    "Unable to submit the reinstatement request."
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

            setSuccess(
                responseData.message ||
                "Your reinstatement request has been submitted successfully."
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
                "Reinstatement request error:",
                err
            );

            // =================================================
            // SERVER ERROR
            // =================================================

            if (
                err.response &&
                err.response.data
            ) {
                const responseData =
                    err.response.data;

                setError(
                    responseData.error ||
                    responseData.message ||
                    "Unable to submit the reinstatement request."
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
                            alt="Pio Duran Logo"
                        />

                    </div>

                    <div>

                        <h1 className="government-title">
                            Pio Duran Online Registration
                            and Applicant Services
                        </h1>

                        <p className="government-subtitle">
                            Online Registration and Applicant Services
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
                        className="active"
                    >
                        Reinstatement
                    </button>

                </div>

            </nav>


            {/* =================================================
                MAIN
            ================================================= */}

            <main className="verify-main">

                <div className="verify-container">

                    <div className="page-header">

                        <h1>
                            Reinstatement
                        </h1>

                        <p>
                            Request the reinstatement of a
                            previously cancelled or inactive
                            registration.
                        </p>

                    </div>


                    <div className="verify-card">

                        <div className="card-header-government">

                            <h2>
                                Reinstatement Request
                            </h2>

                            <p>
                                Enter your applicant information
                                and explain the reason for your
                                request.
                            </p>

                        </div>


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
                                        Reinstatement Request Submitted
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

                                    {requestStatus ===
                                        "WAITING FOR INTERNET" ? (
                                        <p>
                                            Your request is securely
                                            stored on this device.
                                            It will be automatically
                                            submitted to the registration
                                            server once an internet
                                            connection is restored.
                                        </p>
                                    ) : (
                                        <p>
                                            Your request is now pending
                                            review by the registration
                                            office. Please wait for the
                                            request to be reviewed.
                                        </p>
                                    )}

                                </div>
                            )}


                            {/* =================================================
                                FORM
                            ================================================= */}

                            <form
                                onSubmit={handleSubmit}
                            >

                                {/* =================================================
                                    APPLICANT INFORMATION
                                ================================================= */}

                                <section className="form-section">

                                    <h3 className="section-title">
                                        Applicant Information
                                    </h3>


                                    <div className="form-grid">

                                        {/* LAST NAME */}

                                        <div className="form-field">

                                            <label className="form-label">
                                                Last Name
                                            </label>

                                            <input
                                                name="lastname"
                                                type="text"
                                                className="form-control"
                                                value={
                                                    formData.lastname
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                placeholder="Enter last name"
                                                autoComplete="family-name"
                                                disabled={
                                                    submitting
                                                }
                                                required
                                            />

                                        </div>


                                        {/* FIRST NAME */}

                                        <div className="form-field">

                                            <label className="form-label">
                                                First Name
                                            </label>

                                            <input
                                                name="firstname"
                                                type="text"
                                                className="form-control"
                                                value={
                                                    formData.firstname
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                placeholder="Enter first name"
                                                autoComplete="given-name"
                                                disabled={
                                                    submitting
                                                }
                                                required
                                            />

                                        </div>


                                        {/* MIDDLE NAME */}

                                        <div className="form-field">

                                            <label className="form-label">
                                                Middle Name
                                            </label>

                                            <input
                                                name="middlename"
                                                type="text"
                                                className="form-control"
                                                value={
                                                    formData.middlename
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                placeholder="Enter middle name"
                                                autoComplete="additional-name"
                                                disabled={
                                                    submitting
                                                }
                                                required
                                            />

                                        </div>


                                        {/* BIRTHDATE */}

                                        <div className="form-field">

                                            <label className="form-label">
                                                Birthdate
                                            </label>

                                            <input
                                                name="birthdate"
                                                type="date"
                                                className="form-control"
                                                value={
                                                    formData.birthdate
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                disabled={
                                                    submitting
                                                }
                                                required
                                            />

                                        </div>

                                    </div>

                                </section>


                                {/* =================================================
                                    REASON
                                ================================================= */}

                                <section className="form-section">

                                    <h3 className="section-title">
                                        Reason for Reinstatement
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
                                            name="reason"
                                            rows="6"
                                            className="form-control"
                                            value={
                                                formData.reason
                                            }
                                            onChange={
                                                handleChange
                                            }
                                            placeholder="Explain why you are requesting reinstatement"
                                            disabled={
                                                submitting
                                            }
                                            required
                                        />

                                    </div>

                                </section>


                                {/* =================================================
                                    OFFLINE INFORMATION
                                ================================================= */}

                                <div className="information-notice">

                                    <strong>
                                        Important Information
                                    </strong>

                                    <div>
                                        Your existing registration
                                        will not be changed immediately
                                        after submitting this request.
                                    </div>

                                    <div>
                                        The request must first be reviewed
                                        by the registration office.
                                    </div>

                                    <div>
                                        If there is no internet connection,
                                        your request will be saved securely
                                        on this device and submitted
                                        automatically when the connection
                                        returns.
                                    </div>

                                </div>


                                {/* =================================================
                                    ACTIONS
                                ================================================= */}

                                <div className="form-actions">

                                    <button
                                        type="submit"
                                        className="btn-government"
                                        disabled={
                                            submitting
                                        }
                                    >
                                        {submitting
                                            ? "Submitting..."
                                            : "Submit Reinstatement Request"
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

            <footer className="site-footer">

                <div className="site-footer-inner">

                    <div className="footer-title">
                        Pio Duran Online Registration
                    </div>

                    <p>
                        Online Registration and Applicant Services
                    </p>

                </div>

            </footer>

        </div>
    );
};

export default Reinstatement;