
import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const API_BASE_URL = "https://pio-duran-online-registration.onrender.com";

function VerifyApplicant() {
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        lastname: "",
        firstname: "",
        middlename: "",
        birthdate: "",
    });

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [result, setResult] = useState(null);

    /*
    =========================================================
    HANDLE INPUT
    =========================================================
    */

    const handleChange = (e) => {
        const {
            name,
            value,
        } = e.target;

        setFormData((previous) => ({
            ...previous,
            [name]: value,
        }));

        setError("");
        setResult(null);
    };

    /*
    =========================================================
    VERIFY APPLICANT
    =========================================================
    */

    const handleSubmit = async (e) => {
        e.preventDefault();

        setError("");
        setResult(null);

        if (
            !formData.lastname.trim() ||
            !formData.firstname.trim() ||
            !formData.middlename.trim() ||
            !formData.birthdate
        ) {
            setError(
                "Please complete all required fields."
            );

            return;
        }

        setLoading(true);

        try {
            const data = new URLSearchParams();

            data.append(
                "lastname",
                formData.lastname.trim()
            );

            data.append(
                "firstname",
                formData.firstname.trim()
            );

            data.append(
                "middlename",
                formData.middlename.trim()
            );

            data.append(
                "birthdate",
                formData.birthdate
            );

            const response = await axios.post(
                `${API_BASE_URL}/api/applicant/verify-new-registration/`,
                data,
                {
                    headers: {
                        "Content-Type":
                            "application/x-www-form-urlencoded",
                    },
                }
            );

            setResult(response.data);

        } catch (err) {

            if (err.response?.data?.message) {

                setError(
                    err.response.data.message
                );

            } else {

                setError(
                    "Unable to connect to the server. Please check your Internet connection."
                );
            }

        } finally {
            setLoading(false);
        }
    };

    /*
    =========================================================
    CONTINUE TO NEW REGISTRATION
    =========================================================
    */

    const continueToRegistration = () => {

        navigate(
            "/new-registration",
            {
                state: {
                    verifiedApplicant: {
                        lastname:
                            formData.lastname.trim(),

                        firstname:
                            formData.firstname.trim(),

                        middlename:
                            formData.middlename.trim(),

                        birthdate:
                            formData.birthdate,
                    },
                },
            }
        );
    };

    /*
    =========================================================
    RETURN TO HOME
    =========================================================
    */

    const returnToHome = () => {
        navigate("/");
    };

    /*
    =========================================================
    RENDER
    =========================================================
    */

    return (
        <div className="verify-page">

            {/* =================================================
                GOVERNMENT HEADER
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
                        onClick={returnToHome}
                    >
                        Home
                    </button>

                    <button
                        type="button"
                        className="active"
                    >
                        New Registration
                    </button>

                </div>

            </nav>


            {/* =================================================
                MAIN
            ================================================= */}

            <main className="verify-main">

                <div className="verify-container">

                    {/* =========================================
                        BACK BUTTON
                    ========================================= */}

                    <div className="verify-back-button">

                        <button
                            type="button"
                            className="back-button-government"
                            onClick={returnToHome}
                        >
                            ← Back to Home
                        </button>

                    </div>


                    {/* =========================================
                        PAGE HEADER
                    ========================================= */}

                    <div className="page-header">

                        <h1>
                            Verify Applicant
                        </h1>

                        <p>
                            Before starting a new registration,
                            please verify that you do not already
                            have an existing applicant record.
                        </p>

                    </div>


                    {/* =========================================
                        ERROR
                    ========================================= */}

                    {error && (

                        <div className="error-box">

                            <div className="error-box-title">
                                Verification Error
                            </div>

                            <p>
                                {error}
                            </p>

                        </div>

                    )}


                    {/* =========================================
                        MAIN CARD
                    ========================================= */}

                    <div className="verify-card">

                        {/* =====================================
                            CARD HEADER
                        ===================================== */}

                        <div className="card-header-government">

                            <h2>
                                Registration Verification
                            </h2>

                            <p>
                                Enter your information exactly as
                                it appears on your official documents
                                to search for an existing registration.
                            </p>

                        </div>


                        {/* =====================================
                            CARD BODY
                        ===================================== */}

                        <div className="card-body-government">

                            <form
                                onSubmit={handleSubmit}
                            >

                                {/* =================================
                                    APPLICANT INFORMATION
                                ================================= */}

                                <section className="form-section">

                                    <h3 className="section-title">
                                        Applicant Information
                                    </h3>

                                    <div className="form-grid">

                                        {/* LAST NAME */}

                                        <div className="form-field">

                                            <label
                                                className="form-label"
                                                htmlFor="lastname"
                                            >
                                                Last Name
                                            </label>

                                            <input
                                                id="lastname"
                                                type="text"
                                                name="lastname"
                                                className="form-control"
                                                value={
                                                    formData.lastname
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                placeholder="Enter last name"
                                                autoComplete="family-name"
                                                disabled={loading}
                                            />

                                        </div>


                                        {/* FIRST NAME */}

                                        <div className="form-field">

                                            <label
                                                className="form-label"
                                                htmlFor="firstname"
                                            >
                                                First Name
                                            </label>

                                            <input
                                                id="firstname"
                                                type="text"
                                                name="firstname"
                                                className="form-control"
                                                value={
                                                    formData.firstname
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                placeholder="Enter first name"
                                                autoComplete="given-name"
                                                disabled={loading}
                                            />

                                        </div>


                                        {/* MIDDLE NAME */}

                                        <div className="form-field">

                                            <label
                                                className="form-label"
                                                htmlFor="middlename"
                                            >
                                                Middle Name
                                            </label>

                                            <input
                                                id="middlename"
                                                type="text"
                                                name="middlename"
                                                className="form-control"
                                                value={
                                                    formData.middlename
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                placeholder="Enter middle name"
                                                autoComplete="additional-name"
                                                disabled={loading}
                                            />

                                        </div>


                                        {/* BIRTHDATE */}

                                        <div className="form-field">

                                            <label
                                                className="form-label"
                                                htmlFor="birthdate"
                                            >
                                                Birthdate
                                            </label>

                                            <input
                                                id="birthdate"
                                                type="date"
                                                name="birthdate"
                                                className="form-control"
                                                value={
                                                    formData.birthdate
                                                }
                                                onChange={
                                                    handleChange
                                                }
                                                disabled={loading}
                                            />

                                        </div>

                                    </div>

                                </section>


                                {/* =================================
                                    RESULT - EXISTING APPLICANT
                                ================================= */}

                                {result &&
                                    result.exists && (

                                    <div className="existing-box">

                                        <h3>
                                            Applicant Already Exists
                                        </h3>

                                        <p>
                                            An applicant with the
                                            same information already
                                            exists in the registration
                                            system.
                                        </p>

                                        <p
                                            style={{
                                                marginTop: "8px",
                                            }}
                                        >
                                            New registration cannot
                                            be submitted.
                                        </p>

                                    </div>

                                )}


                                {/* =================================
                                    RESULT - NO EXISTING APPLICANT
                                ================================= */}

                                {result &&
                                    !result.exists && (

                                    <div className="success-box">

                                        <div className="success-box-title">
                                            No Existing Applicant Found
                                        </div>

                                        <p>
                                            No existing applicant was
                                            found with the information
                                            provided.
                                        </p>

                                        <p
                                            style={{
                                                marginTop: "8px",
                                            }}
                                        >
                                            You may proceed with
                                            New Registration.
                                        </p>

                                    </div>

                                )}


                                {/* =================================
                                    ACTIONS
                                ================================= */}

                                <div className="form-actions">

                                    {/* VERIFY */}

                                    {!result && (

                                        <button
                                            type="submit"
                                            className="btn-government"
                                            disabled={loading}
                                        >
                                            {loading
                                                ? "Verifying..."
                                                : "Verify Applicant"}
                                        </button>

                                    )}


                                    {/* CONTINUE */}

                                    {result &&
                                        !result.exists && (

                                        <button
                                            type="button"
                                            className="btn-government"
                                            onClick={
                                                continueToRegistration
                                            }
                                        >
                                            Continue to New Registration
                                        </button>

                                    )}


                                    {/* RETURN */}

                                    {result &&
                                        result.exists && (

                                        <button
                                            type="button"
                                            className="btn-secondary-government"
                                            onClick={
                                                returnToHome
                                            }
                                        >
                                            Return to Home
                                        </button>

                                    )}

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
}

export default VerifyApplicant;