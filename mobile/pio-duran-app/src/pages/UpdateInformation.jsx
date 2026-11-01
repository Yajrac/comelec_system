import RequestProfileFields from "../components/RequestProfileFields";
import { initialRequestProfile, requestProfileError } from "../utils/requestProfile";
import { calculateAge } from "../utils/calculateAge";
import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { submitWithOfflineSupport } from "../services/apiRequest";
import "./UpdateInformation.css";

import LookupModal from "../components/LookupModal";

const API_BASE_URL =
    import.meta.env.VITE_API_URL ||
    "http://localhost:8000";

function UpdateInformation() {
    const navigate = useNavigate();

    const [step, setStep] = useState(1);
    const [applicant, setApplicant] = useState(null);
    const [barangays, setBarangays] = useState([]);

    const [searchData, setSearchData] = useState({ registration_reference: "" });

    const [profile, setProfile] = useState(() => initialRequestProfile(null));

    const [formData, setFormData] = useState({
        lastname: "",
        firstname: "",
        middlename: "",
        age: "",
        sex: "",
        birthdate: "",
        birthplace: "",
        brgy: "",
        province: "Albay",
        municipality: "Pio Duran",
        phone: "",
        email: "",
        civil_status: "Single",
        pwd_status: "NO",
        citizenship_status: "BY_BIRTH",
        father: "",
        mother: "",
        reason: "",
    });

    const [loading, setLoading] = useState(false);
    const [loadingBarangays, setLoadingBarangays] = useState(false);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const [requestId, setRequestId] = useState("");
    const [requestStatus, setRequestStatus] = useState("");
    const [isOfflineRequest, setIsOfflineRequest] = useState(false);

    useEffect(() => {
        const age = calculateAge(formData.birthdate);
        setFormData(previous => previous.age === age ? previous : { ...previous, age });
    }, [formData.birthdate]);

    const handleSearchChange = (e) => {
        const { name, value } = e.target;

        setSearchData((previous) => ({
            ...previous,
            [name]: value,
        }));
    };

    const handleFormChange = (e) => {
        const { name, value } = e.target;

        setFormData((previous) => ({
            ...previous,
            [name]: value,
        }));
    };

    const loadBarangays = async () => {
        setLoadingBarangays(true);

        try {
            const response = await axios.get(
                `${API_BASE_URL}/api/barangays/`,
                {
                    timeout: 15000,
                }
            );

            if (Array.isArray(response.data)) {
                setBarangays(response.data);
            } else if (
                Array.isArray(response.data?.barangays)
            ) {
                setBarangays(response.data.barangays);
            } else if (
                Array.isArray(response.data?.data)
            ) {
                setBarangays(response.data.data);
            } else {
                setBarangays([]);
            }
        } catch (err) {
            console.error(
                "Barangay loading error:",
                err
            );

            setError(
                "Unable to load the barangay list. Please check your internet connection and try again."
            );
        } finally {
            setLoadingBarangays(false);
        }
    };

    const handleFindApplicant = async (e) => {
        e.preventDefault();

        setError("");
        setSuccess("");
        setRequestId("");
        setRequestStatus("");
        setIsOfflineRequest(false);

        if (!/^PD-[A-F0-9]{32}$/i.test(searchData.registration_reference.trim())) {
            setError("Enter PD- followed by exactly 32 hexadecimal characters."); return;
        }

        setLoading(true);

        try {
            const response = await axios.post(
                `${API_BASE_URL}/api/applicants/find/`,
                { registration_reference: searchData.registration_reference.trim().toUpperCase(), request_type: "UPDATE_INFORMATION" },
                {
                    timeout: 15000,

                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                }
            );

            const responseData =
                response.data;

            if (
                !responseData?.success ||
                !responseData?.applicant
            ) {
                setError(
                    responseData?.error ||
                        responseData?.message ||
                        "No approved registration was found using the information provided."
                );

                return;
            }

            const foundApplicant =
                responseData.applicant;

            setApplicant(foundApplicant);
            setProfile(initialRequestProfile(foundApplicant));

            setFormData({
                civil_status: foundApplicant.civil_status || "Single",
                lastname:
                    foundApplicant.lastname || "",

                firstname:
                    foundApplicant.firstname || "",

                middlename:
                    foundApplicant.middlename || "",

                age:
                    foundApplicant.age ?? "",

                sex:
                    (foundApplicant.sex || "").toUpperCase(),

                birthdate:
                    foundApplicant.birthdate || "",

                birthplace:
                    foundApplicant.birthplace || "",

                brgy:
                    foundApplicant.brgy?.id ??
                    foundApplicant.brgy ??
                    "",

                province:
                    foundApplicant.province ||
                    "Albay",

                municipality:
                    foundApplicant.municipality ||
                    "Pio Duran",

                phone:
                    foundApplicant.phone || "",

                email:
                    foundApplicant.email || "",

                pwd_status:
                    foundApplicant.pwd_status ||
                    "NO",

                citizenship_status:
                    foundApplicant.citizenship_status ||
                    "BY_BIRTH",

                father:
                    foundApplicant.father || "",

                mother:
                    foundApplicant.mother || "",

                reason: "",
            });

            setStep(2);

            await loadBarangays();
        } catch (err) {
            console.error(
                "Find applicant error:",
                err
            );

            if (err.response) {
                const responseData =
                    err.response.data;

                setError(
                    responseData?.error ||
                        responseData?.message ||
                        "Unable to find the applicant."
                );
            } else {
                setError(
                    "Unable to connect to the server. Please check your internet connection and try again."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    const validateForm = () => {
        if (!formData.lastname.trim()) {
            return "Please enter the last name.";
        }

        if (!formData.firstname.trim()) {
            return "Please enter the first name.";
        }



        if (!formData.age) {
            return "Please enter the age.";
        }

        if (!formData.sex) {
            return "Please select the sex.";
        }

        if (!formData.birthdate) {
            return "Please enter the birthdate.";
        }

        if (!formData.birthplace.trim()) {
            return "Please enter the birthplace.";
        }

        if (!formData.brgy) {
            return "Please select the barangay.";
        }

        if (!formData.province.trim()) {
            return "Please enter the province.";
        }

        if (!formData.municipality.trim()) {
            return "Please enter the municipality.";
        }

        if (!formData.phone.trim()) {
            return "Please enter the contact number.";
        }





        if (!formData.reason.trim()) {
            return "Please provide the reason for the update.";
        }

        return "";
    };

    const resetForm = () => {
        setApplicant(null);
        setProfile(initialRequestProfile(null));

        setStep(1);

        setSearchData({ registration_reference: "" });

        setFormData({
            lastname: "",
            firstname: "",
            middlename: "",
            age: "",
            sex: "",
            birthdate: "",
            birthplace: "",
            brgy: "",
            province: "Albay",
            municipality: "Pio Duran",
            phone: "",
            email: "",
            civil_status: "Single",
        pwd_status: "NO",
            citizenship_status: "BY_BIRTH",
            father: "",
            mother: "",
            reason: "",
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const profileError = requestProfileError(profile, applicant);
        if (profileError) { setError(profileError); return; }


        setError("");
        setSuccess("");
        setRequestId("");
        setRequestStatus("");
        setIsOfflineRequest(false);

        if (!applicant) {
            setError(
                "No applicant record has been selected."
            );
            return;
        }

        const validationError =
            validateForm();

        if (validationError) {
            setError(validationError);
            return;
        }

        setLoading(true);

        const payload = {
            ...profile,
            civil_status: formData.civil_status,
            applicant_id: applicant.id,

            lastname:
                formData.lastname.trim(),

            firstname:
                formData.firstname.trim(),

            middlename:
                formData.middlename.trim(),

            age: Number(formData.age),

            sex:
                formData.sex,

            birthdate:
                formData.birthdate,

            birthplace:
                formData.birthplace.trim(),

            brgy:
                formData.brgy
                    ? Number(formData.brgy)
                    : null,

            province:
                formData.province.trim(),

            municipality:
                formData.municipality.trim(),

            phone:
                formData.phone.trim(),

            email:
                formData.email.trim(),

            pwd_status:
                formData.pwd_status,

            citizenship_status:
                formData.citizenship_status,

            father:
                formData.father.trim(),

            mother:
                formData.mother.trim(),

            reason:
                formData.reason.trim(),

            status: "PENDING",
        };

        try {
            const result =
                await submitWithOfflineSupport({
                    requestType:
                        "UPDATE_INFORMATION",

                    endpoint:
                        "/api/applicant-update-requests/",

                    payload,
                });

            if (result.offline) {
                setIsOfflineRequest(true);

                setSuccess(
                    "Your update/correction request has been saved on this device. It will automatically be submitted when your internet connection is restored."
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

            const responseData =
                result.data || {};

            setIsOfflineRequest(false);

            setSuccess(
                responseData.message ||
                    "Your update/correction request has been submitted successfully and is now pending review."
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
                "Update information request error:",
                err
            );

            if (err.response) {
                const responseData =
                    err.response.data;

                setError(
                    responseData?.error ||
                        responseData?.message ||
                        "Unable to submit the update request."
                );
            } else {
                setError(
                    "Unable to submit the request. Please check your internet connection and try again."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        setError("");
        setSuccess("");
        setRequestId("");
        setRequestStatus("");
        setIsOfflineRequest(false);

        setApplicant(null);
        setStep(1);
    };

    return (
        <div className="update-page">
            {step === 1 && <LookupModal checking={loading} message={error} onClose={() => setError("")} />}

            {/* =====================================================
                HEADER
            ===================================================== */}




            {/* =====================================================
                NAVIGATION
            ===================================================== */}




            {/* =====================================================
                STEP INDICATOR
            ===================================================== */}

            <div className="step-wrapper">

                <div
                    className={`step ${
                        step === 1
                            ? "active"
                            : "completed"
                    }`}
                >
                    <div className="step-number">
                        1
                    </div>

                    <div className="step-label">
                        Find Registration
                    </div>
                </div>

                <div
                    className={`step-line ${
                        step === 2
                            ? "completed"
                            : ""
                    }`}
                />

                <div
                    className={`step ${
                        step === 2
                            ? "active"
                            : ""
                    }`}
                >
                    <div className="step-number">
                        2
                    </div>

                    <div className="step-label">
                        Update Information
                    </div>
                </div>

            </div>


            {/* =====================================================
                ALERTS
            ===================================================== */}

            {(success || error) && (
                <div className="alert-container">

                    {success && (
                        <div
                            className={`success-alert ${
                                isOfflineRequest
                                    ? "offline-success"
                                    : ""
                            }`}
                        >
                            <strong>
                                {isOfflineRequest
                                    ? "Request Saved Offline"
                                    : "Request Submitted Successfully"}
                            </strong>

                            <div>
                                {success}
                            </div>

                            {requestId && (
                                <div
                                    className={
                                        isOfflineRequest
                                            ? "offline-details"
                                            : "online-details"
                                    }
                                >
                                    <strong
                                        style={{
                                            display:
                                                "inline",
                                            marginRight:
                                                "6px",
                                            fontSize:
                                                "14px",
                                        }}
                                    >
                                        Reference:
                                    </strong>

                                    #{requestId}
                                </div>
                            )}

                            {requestStatus && (
                                <div>
                                    <strong
                                        style={{
                                            display:
                                                "inline",
                                            marginRight:
                                                "6px",
                                            fontSize:
                                                "14px",
                                        }}
                                    >
                                        Status:
                                    </strong>

                                    {requestStatus}
                                </div>
                            )}
                        </div>
                    )}

                    {error && (
                        <div className="error-alert">

                            <strong>
                                Unable to Continue
                            </strong>

                            <div>
                                {error}
                            </div>

                        </div>
                    )}

                </div>
            )}


            {/* =====================================================
                MAIN
            ===================================================== */}

            <main className="update-main">
                <div className="page-header"><h1>Update Information</h1><p>Request a correction or update to your registration details.</p></div>

                <div className="form-card">

                    {/* =================================================
                        STEP 1
                    ================================================= */}

                    {!applicant && (
                        <>
                            <div className="form-card-header">

                                <h2>
                                    Find Your Registration
                                </h2>

                                <p>
                                    Enter your existing
                                    registration information
                                    to locate your record.
                                </p>

                            </div>

                            <div className="form-card-body">

                                <form
                                    onSubmit={
                                        handleFindApplicant
                                    }
                                >

                                    <div className="section-title">
                                        Applicant Information
                                    </div>

                                    <div className="form-grid search-grid"><div className="form-group full-width"><label htmlFor="registration_reference">Registration Reference Number <span>*</span></label><input id="registration_reference" className="form-control" name="registration_reference" value={searchData.registration_reference} onChange={handleSearchChange} placeholder="PD-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" maxLength={35} required autoCapitalize="characters" autoCorrect="off" spellCheck={false} /><p className="form-text">Use the reference number from your registration confirmation.</p></div></div>

<div className="information-notice mobile-info-notice">
                                        <svg className="mobile-info-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v1" /></svg>

                                        <strong>
                                            Important Information
                                        </strong>

                                        <div>
                                            Only an existing
                                            approved registration
                                            can be used for an
                                            information update
                                            request.
                                        </div>

                                        <div>
                                            Your existing
                                            registration will not
                                            be changed simply by
                                            searching for your
                                            record.
                                        </div>

                                    </div>


                                    <div className="button-row">

                                        <button
                                            type="button"
                                            className="btn btn-secondary"
                                            onClick={() =>
                                                navigate("/")
                                            }
                                        >
                                            Back
                                        </button>

                                        <button
                                            type="submit"
                                            className="btn btn-government"
                                            disabled={loading || !searchData.registration_reference.trim()}
                                            aria-busy={loading}
                                        >
                                            {loading && <span className="mobile-loading-spinner" aria-hidden="true" />}
                                            {loading
                                                ? "Searching..."
                                                : "Find Registration"}
                                        </button>

                                    </div>

                                </form>

                            </div>
                        </>
                    )}


                    {/* =================================================
                        STEP 2
                    ================================================= */}

                    {applicant && (
                        <>
                            <div className="form-card-header">

                                <h2>
                                    Update Registration Information
                                </h2>

                                <p>
                                    Review your existing
                                    information and provide the
                                    corrections or updates you
                                    want to request.
                                </p>

                            </div>

                            <div className="form-card-body">

                                {/* RECORD FOUND */}

                                <div className="record-found">

                                    <div className="record-found-icon">
                                        ✓
                                    </div>

                                    <div>
                                        <strong>
                                            Registration Record Found
                                        </strong>

                                        Your existing approved
                                        registration has been
                                        located. You may now
                                        review and submit the
                                        information you want to
                                        update.
                                    </div>

                                </div>


                                {/* APPLICANT SUMMARY */}

                                <div className="applicant-summary">

                                    <div className="summary-label">
                                        Existing Registered Applicant
                                    </div>

                                    <div className="summary-name">
                                        {applicant.firstname}{" "}
                                        {applicant.middlename}{" "}
                                        {applicant.lastname}
                                    </div>

                                </div>


                                <form
                                    onSubmit={
                                        handleSubmit
                                    }
                                >
<RequestProfileFields part="photo" profile={profile} setProfile={setProfile} applicant={applicant} />


                                    {/* =================================================
                                        PERSONAL INFORMATION
                                    ================================================= */}

                                    <div className="section-title">
                                        Personal Information
                                    </div>

                                    <div className="form-grid">

                                        <div className="mobile-request-name-row"><div className="mobile-name-grid"><div className="form-group">
                                            <label>
                                                Last Name
                                            </label>

                                            <input
                                                className="form-control"
                                                type="text"
                                                name="lastname" required
                                                value={
                                                    formData.lastname
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div><div className="form-group">
                                            <label>
                                                First Name
                                            </label>

                                            <input
                                                className="form-control"
                                                type="text"
                                                name="firstname" required
                                                value={
                                                    formData.firstname
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div><div className="form-group">
                                            <label>
                                                Middle Name (optional)
                                            </label>

                                            <input
                                                className="form-control"
                                                type="text"
                                                name="middlename"
                                                value={
                                                    formData.middlename
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div><div className="form-group mobile-suffix"><label htmlFor="request_suffix">Suffix <small>(optional)</small></label><select id="request_suffix" name="suffix" className="form-control" value={profile.suffix} onChange={event => setProfile(previous => ({ ...previous, suffix: event.target.value }))}><option value="">None</option>{["Jr.", "Sr.", "II", "III", "IV", "V"].map(value => <option key={value}>{value}</option>)}</select></div></div><RequestProfileFields part="flags" profile={profile} setProfile={setProfile} applicant={applicant} /></div>

                                        <div className="form-group">
                                            <label>
                                                Birthdate
                                            </label>

                                            <input
                                                className="form-control"
                                                type="date"
                                                name="birthdate" required
                                                value={
                                                    formData.birthdate
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div>
<div className="form-group">
                                            <label>
                                                Age
                                            </label>

                                            <input
                                                className="form-control"
                                                type="number"
                                                name="age" readOnly
                                                min="18"
                                                value={
                                                    formData.age
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div>

                                        <div className="form-group">
                                            <label>
                                                Sex
                                            </label>

                                            <select
                                                className="form-control"
                                                name="sex" required
                                                value={
                                                    formData.sex
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            >
                                                <option value="">
                                                    Select Sex
                                                </option>

                                                <option value="MALE">
                                                    Male
                                                </option>

                                                <option value="FEMALE">
                                                    Female
                                                </option>
                                            </select>
                                        </div>



                                        <div className="form-group form-group-wide">
                                            <label>
                                                Birthplace
                                            </label>

                                            <input
                                                className="form-control"
                                                type="text"
                                                name="birthplace" required
                                                value={
                                                    formData.birthplace
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                                placeholder="Enter birthplace"
                                            />
                                        </div>

                                    </div>


                                    {/* =================================================
                                        ADDRESS INFORMATION
                                    ================================================= */}

                                    <div className="section-title">
                                        Address Information
                                    </div>

                                    <div className="form-grid">

                                        <div className="form-group form-group-wide">
                                            <label>
                                                Barangay
                                            </label>

                                            <select
                                                className="form-control"
                                                name="brgy" required
                                                value={
                                                    formData.brgy
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                                disabled={
                                                    loadingBarangays
                                                }
                                            >
                                                <option value="">
                                                    {loadingBarangays
                                                        ? "Loading barangays..."
                                                        : "Select Barangay"}
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

                                        <div className="form-group">
                                            <label>
                                                Municipality
                                            </label>

                                            <input
                                                className="form-control"
                                                type="text"
                                                name="municipality"
                                                value={
                                                    formData.municipality
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div>

                                        <div className="form-group">
                                            <label>
                                                Province
                                            </label>

                                            <input
                                                className="form-control"
                                                type="text"
                                                name="province"
                                                value={
                                                    formData.province
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div>

                                    </div>


                                    {/* =================================================
                                        CONTACT INFORMATION
                                    ================================================= */}

                                    <div className="section-title">
                                        Contact Information
                                    </div>

                                    <div className="form-grid">

                                        <div className="form-group">
                                            <label>
                                                Contact Number
                                            </label>

                                            <input
                                                className="form-control"
                                                type="tel"
                                                name="phone" required
                                                value={
                                                    formData.phone
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                                placeholder="09XXXXXXXXX"
                                            />
                                        </div>

                                        <div className="form-group form-group-wide">
                                            <label>
                                                Email Address (optional)
                                            </label>

                                            <input
                                                className="form-control"
                                                type="email"
                                                name="email"
                                                value={
                                                    formData.email
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                                placeholder="Enter email address"
                                            />
                                        </div>

                                    </div>


                                    {/* =================================================
                                        OTHER INFORMATION
                                    ================================================= */}

                                    <div className="section-title">
                                        Other Information
                                    </div>

                                    <div className="form-grid">

                                        <div className="form-group"><label htmlFor="civil_status">Civil Status <span>*</span></label><select id="civil_status" name="civil_status" className="form-control" value={formData.civil_status} onChange={handleFormChange} required>{["Single", "Married", "Widowed", "Separated"].map(value => <option key={value}>{value}</option>)}</select></div>
<div className="form-group form-group-wide">
                                            <label>
                                                PWD Status
                                            </label>

                                            <select
                                                className="form-control"
                                                name="pwd_status" required
                                                value={
                                                    formData.pwd_status
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            ><option value="NO">Not PWD</option><option value="VISUAL">Visual Disability</option><option value="HEARING">Hearing Disability</option><option value="PHYSICAL">Physical Disability</option><option value="INTELLECTUAL">Intellectual Disability</option><option value="PSYCHOSOCIAL">Psychosocial Disability</option><option value="MULTIPLE">Multiple Disabilities</option><option value="OTHER">Other</option></select>
                                        </div>

                                        <div className="form-group form-group-wide">
                                            <label>
                                                Citizenship
                                            </label>

                                            <select
                                                className="form-control"
                                                name="citizenship_status" required
                                                value={
                                                    formData.citizenship_status
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            >
                                                <option value="BY_BIRTH">
                                                    By Birth
                                                </option>

                                                <option value="NATURALIZED">
                                                    Naturalized
                                                </option>
                                            </select>
                                        </div>

                                        <div className="form-group form-group-wide">
                                            <label>
                                                Father's Name <small>(optional)</small>
                                            </label>

                                            <input
                                                className="form-control"
                                                type="text"
                                                name="father"
                                                value={
                                                    formData.father
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div>

                                        <div className="form-group form-group-wide">
                                            <label>
                                                Mother's Name <small>(optional)</small>
                                            </label>

                                            <input
                                                className="form-control"
                                                type="text"
                                                name="mother"
                                                value={
                                                    formData.mother
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                            />
                                        </div>

                                    </div>


                                    {/* =================================================
                                        REQUEST DETAILS
                                    ================================================= */}

                                    <div className="section-title">
                                        Request Details
                                    </div>

                                    <div className="form-grid">

                                        <div className="form-group form-group-wide">
                                            <label>
                                                Reason for Update
                                            </label>

                                            <textarea
                                                className="form-control"
                                                name="reason" required minLength={5} maxLength={2000}
                                                value={
                                                    formData.reason
                                                }
                                                onChange={
                                                    handleFormChange
                                                }
                                                placeholder="Explain the information that needs to be corrected or updated."
                                            />
                                        </div>

                                    </div>


                                    {/* =================================================
                                        INFORMATION NOTICE
                                    ================================================= */}

                                    <div className="information-notice mobile-info-notice">
                                        <svg className="mobile-info-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v1" /></svg>

                                        <strong>
                                            Important Information
                                        </strong>

                                        <div>
                                            Submitting this request
                                            does not immediately
                                            change your existing
                                            registration record.
                                        </div>

                                        <div>
                                            Your request will be
                                            reviewed by the
                                            registration office
                                            before any changes are
                                            applied.
                                        </div>

                                        <div>
                                            The existing
                                            registration remains
                                            unchanged while the
                                            request is pending.
                                        </div>

                                    </div>


                                    {/* =================================================
                                        BUTTONS
                                    ================================================= */}

                                    <RequestProfileFields part="documents" profile={profile} setProfile={setProfile} applicant={applicant} />
<div className="button-row">

                                        <button
                                            type="button"
                                            className="btn btn-secondary"
                                            onClick={
                                                handleBack
                                            }
                                            disabled={loading}
                                        >
                                            Back
                                        </button>

                                        <button
                                            type="submit"
                                            className="btn btn-submit"
                                            disabled={loading}
                                        >
                                            {loading
                                                ? "Submitting..."
                                                : "Submit Update Request"}
                                        </button>

                                    </div>

                                </form>

                            </div>
                        </>
                    )}

                </div>

            </main>


            {/* =====================================================
                FOOTER
            ===================================================== */}


        </div>
    );
}

export default UpdateInformation;
