import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

const RegistrationSuccessful = () => {
    const location = useLocation();
    const navigate = useNavigate();

    const applicant = location.state?.applicant;

    if (!applicant) {
        return (
            <div className="container py-4">
                <div className="alert alert-danger">
                    Registration information could not be found.
                </div>

                <button
                    className="btn btn-primary"
                    onClick={() => navigate("/verify-applicant")}
                >
                    Return to New Registration
                </button>
            </div>
        );
    }

    return (
        <>
            <style>{`
                /* =========================================================
                   PAGE HEADER
                ========================================================= */

                .page-header {
                    margin-bottom: 28px;
                }

                .page-header h1 {
                    font-size: 28px;
                    font-weight: 700;
                    color: #002b7f;
                    margin-bottom: 6px;
                }

                .page-header p {
                    color: #6c757d;
                    margin: 0;
                }

                /* =========================================================
                   SUCCESS CARD
                ========================================================= */

                .success-card {
                    background: #ffffff;
                    border: 1px solid #dee2e6;
                    border-top: 5px solid #0038a8;
                    border-radius: 6px;
                    box-shadow: 0 3px 12px rgba(0, 0, 0, 0.06);
                    overflow: hidden;
                }

                .success-header {
                    background: #f4f8ff;
                    padding: 28px 30px;
                    border-bottom: 1px solid #dee2e6;
                }

                .success-title {
                    display: flex;
                    align-items: center;
                    gap: 14px;
                }

                .success-icon {
                    width: 46px;
                    height: 46px;
                    border-radius: 50%;
                    background: #0038a8;
                    color: #ffffff;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 24px;
                    font-weight: 700;
                    flex-shrink: 0;
                }

                .success-header h2 {
                    margin: 0;
                    font-size: 22px;
                    font-weight: 700;
                    color: #002b7f;
                }

                .success-header p {
                    margin: 5px 0 0;
                    color: #6c757d;
                    font-size: 14px;
                }

                /* =========================================================
                   BODY
                ========================================================= */

                .success-body {
                    padding: 30px;
                }

                /* =========================================================
                   SECTION
                ========================================================= */

                .info-section {
                    margin-bottom: 30px;
                }

                .section-title {
                    font-size: 17px;
                    font-weight: 700;
                    color: #002b7f;
                    margin-bottom: 18px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #e9ecef;
                }

                /* =========================================================
                   APPLICATION INFORMATION
                ========================================================= */

                .application-summary {
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    padding: 20px;
                }

                .detail-item {
                    margin-bottom: 16px;
                }

                .detail-item:last-child {
                    margin-bottom: 0;
                }

                .detail-label {
                    display: block;
                    color: #6c757d;
                    font-size: 12px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.4px;
                    margin-bottom: 5px;
                }

                .detail-value {
                    color: #212529;
                    font-size: 15px;
                    font-weight: 600;
                    word-break: break-word;
                }

                /* =========================================================
                   STATUS
                ========================================================= */

                .status-badge {
                    display: inline-block;
                    padding: 6px 12px;
                    background: #fff3cd;
                    border: 1px solid #ffecb5;
                    color: #664d03;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: 700;
                }

                /* =========================================================
                   INFORMATION CARD
                ========================================================= */

                .info-card {
                    border: 1px solid #dee2e6;
                    background: #ffffff;
                    padding: 20px;
                }

                /* =========================================================
                   NOTICE
                ========================================================= */

                .notice-box {
                    background: #f4f8ff;
                    border: 1px solid #b6d4fe;
                    border-left: 5px solid #0038a8;
                    padding: 18px 20px;
                    margin-top: 4px;
                    margin-bottom: 28px;
                }

                .notice-box p {
                    margin: 0 0 7px;
                    color: #084298;
                    line-height: 1.6;
                }

                .notice-box p:last-child {
                    margin-bottom: 0;
                }

                /* =========================================================
                   ACTION
                ========================================================= */

                .action-area {
                    padding-top: 4px;
                }

                .btn-government {
                    display: inline-block;
                    background: #0038a8;
                    border: 1px solid #0038a8;
                    color: #ffffff;
                    padding: 11px 22px;
                    font-size: 14px;
                    font-weight: 600;
                    text-decoration: none;
                    border-radius: 4px;
                    transition: background 0.2s ease;
                    cursor: pointer;
                }

                .btn-government:hover {
                    background: #002b7f;
                    border-color: #002b7f;
                    color: #ffffff;
                }

                /* =========================================================
                   RESPONSIVE
                ========================================================= */

                @media (max-width: 767.98px) {

                    .page-header h1 {
                        font-size: 24px;
                    }

                    .success-header {
                        padding: 22px;
                    }

                    .success-body {
                        padding: 22px;
                    }

                    .success-title {
                        align-items: flex-start;
                    }

                    .success-icon {
                        width: 40px;
                        height: 40px;
                        font-size: 20px;
                    }

                    .success-header h2 {
                        font-size: 19px;
                    }

                    .info-card,
                    .application-summary {
                        padding: 16px;
                    }
                }
            `}</style>

            <div className="container py-4">

                {/* =====================================================
                    PAGE HEADER
                ===================================================== */}

                <div className="page-header">

                    <h1>
                        Registration Successful
                    </h1>

                    <p>
                        The applicant has been successfully registered.
                    </p>

                </div>

                {/* =====================================================
                    SUCCESS CARD
                ===================================================== */}

                <div className="success-card">

                    {/* HEADER */}

                    <div className="success-header">

                        <div className="success-title">

                            <div className="success-icon">
                                ✓
                            </div>

                            <div>

                                <h2>
                                    Registration Successfully Submitted
                                </h2>

                                <p>
                                    Please keep the following information
                                    for your records.
                                </p>

                            </div>

                        </div>

                    </div>

                    {/* BODY */}

                    <div className="success-body">

                        {/* =================================================
                            APPLICATION INFORMATION
                        ================================================= */}

                        <div className="info-section">

                            <h3 className="section-title">
                                Application Information
                            </h3>

                            <div className="application-summary">

                                <div className="row">

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Application Type
                                        </span>

                                        <div className="detail-value">
                                            {applicant.application_type_display ||
                                                "New Registration"}
                                        </div>

                                    </div>

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Status
                                        </span>

                                        <div className="detail-value">

                                            <span className="status-badge">
                                                {applicant.status_display ||
                                                    applicant.status ||
                                                    "Pending"}
                                            </span>

                                        </div>

                                    </div>

                                </div>

                            </div>

                        </div>

                        {/* =================================================
                            APPLICANT INFORMATION
                        ================================================= */}

                        <div className="info-section">

                            <h3 className="section-title">
                                Applicant Information
                            </h3>

                            <div className="info-card">

                                <div className="row">

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Name
                                        </span>

                                        <div className="detail-value">
                                            {applicant.lastname},{" "}
                                            {applicant.firstname}{" "}
                                            {applicant.middlename}
                                        </div>

                                    </div>

                                    <div className="col-md-3 detail-item">

                                        <span className="detail-label">
                                            Age
                                        </span>

                                        <div className="detail-value">
                                            {applicant.age}
                                        </div>

                                    </div>

                                    <div className="col-md-3 detail-item">

                                        <span className="detail-label">
                                            Sex
                                        </span>

                                        <div className="detail-value">
                                            {applicant.sex}
                                        </div>

                                    </div>

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Birthdate
                                        </span>

                                        <div className="detail-value">
                                            {applicant.birthdate}
                                        </div>

                                    </div>

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Birthplace
                                        </span>

                                        <div className="detail-value">
                                            {applicant.birthplace}
                                        </div>

                                    </div>

                                </div>

                            </div>

                        </div>

                        {/* =================================================
                            ADDRESS
                        ================================================= */}

                        <div className="info-section">

                            <h3 className="section-title">
                                Address
                            </h3>

                            <div className="info-card">

                                <div className="row">

                                    <div className="col-md-4 detail-item">

                                        <span className="detail-label">
                                            Barangay
                                        </span>

                                        <div className="detail-value">
                                            {applicant.brgy_name ||
                                                applicant.brgy ||
                                                "-"}
                                        </div>

                                    </div>

                                    <div className="col-md-4 detail-item">

                                        <span className="detail-label">
                                            Municipality
                                        </span>

                                        <div className="detail-value">
                                            {applicant.municipality ||
                                                "Pio Duran"}
                                        </div>

                                    </div>

                                    <div className="col-md-4 detail-item">

                                        <span className="detail-label">
                                            Province
                                        </span>

                                        <div className="detail-value">
                                            {applicant.province ||
                                                "Albay"}
                                        </div>

                                    </div>

                                </div>

                            </div>

                        </div>

                        {/* =================================================
                            CONTACT INFORMATION
                        ================================================= */}

                        <div className="info-section">

                            <h3 className="section-title">
                                Contact Information
                            </h3>

                            <div className="info-card">

                                <div className="row">

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Phone
                                        </span>

                                        <div className="detail-value">
                                            {applicant.phone}
                                        </div>

                                    </div>

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Email
                                        </span>

                                        <div className="detail-value">
                                            {applicant.email}
                                        </div>

                                    </div>

                                </div>

                            </div>

                        </div>

                        {/* =================================================
                            OTHER INFORMATION
                        ================================================= */}

                        <div className="info-section">

                            <h3 className="section-title">
                                Other Information
                            </h3>

                            <div className="info-card">

                                <div className="row">

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            PWD Status
                                        </span>

                                        <div className="detail-value">
                                            {applicant.pwd_status_display ||
                                                applicant.pwd_status ||
                                                "Not PWD"}
                                        </div>

                                    </div>

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Citizenship
                                        </span>

                                        <div className="detail-value">
                                            {applicant.citizenship_status_display ||
                                                applicant.citizenship_status ||
                                                "By Birth"}
                                        </div>

                                    </div>

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Father's Name
                                        </span>

                                        <div className="detail-value">
                                            {applicant.father}
                                        </div>

                                    </div>

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Mother's Name
                                        </span>

                                        <div className="detail-value">
                                            {applicant.mother}
                                        </div>

                                    </div>

                                    <div className="col-md-6 detail-item">

                                        <span className="detail-label">
                                            Senior Citizen
                                        </span>

                                        <div className="detail-value">

                                            {applicant.is_senior
                                                ? "Yes"
                                                : "No"}

                                        </div>

                                    </div>

                                </div>

                            </div>

                        </div>

                        {/* =================================================
                            NOTICE
                        ================================================= */}

                        <div className="notice-box">

                            <p>
                                Your application is currently{" "}
                                <strong>
                                    {applicant.status_display ||
                                        applicant.status ||
                                        "Pending"}
                                </strong>.
                            </p>

                            <p>
                                Please keep this information for your
                                reference.
                            </p>

                        </div>

                        {/* =================================================
                            ACTION
                        ================================================= */}

                        <div className="action-area">

                            <button
                                type="button"
                                className="btn-government"
                                onClick={() =>
                                    navigate("/verify-new-registration")
                                }
                            >
                                Register Another Applicant
                            </button>

                        </div>

                    </div>

                </div>

            </div>
        </>
    );
};

export default RegistrationSuccessful;