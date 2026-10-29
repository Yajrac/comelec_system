import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./NewRegistration.css";

function NewRegistration() {
    const navigate = useNavigate();

    const [step, setStep] = useState(1);

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
        pwd_status: "NO",
        citizenship_status: "BY_BIRTH",
        father: "",
        mother: "",
    });

    const [barangays, setBarangays] = useState([]);
    const [submittedApplicant, setSubmittedApplicant] = useState(null);

    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [barangayLoading, setBarangayLoading] = useState(true);

    // =========================================================
    // API URLS
    // =========================================================

    const BARANGAY_API =
        "https://pio-duran-online-registration.onrender.com/api/barangays/";

    const REGISTRATION_API =
        "https://pio-duran-online-registration.onrender.com/api/new-registration/";

    // =========================================================
    // LOAD BARANGAYS
    // =========================================================

    useEffect(() => {
        loadBarangays();
    }, []);

    const loadBarangays = async () => {
        setBarangayLoading(true);

        try {
            const response = await axios.get(BARANGAY_API);

            console.log(
                "Barangay API response:",
                response.data
            );

            /*
             * Django barangay_list() returns:
             *
             * [
             *     {
             *         "id": 1,
             *         "name": "Barangay Name"
             *     }
             * ]
             */

            if (Array.isArray(response.data)) {
                setBarangays(response.data);
                setError("");
            } else {
                console.error(
                    "Invalid barangay response:",
                    response.data
                );

                setBarangays([]);

                setError(
                    "Unable to load barangays. Invalid server response."
                );
            }

        } catch (err) {
            console.error(
                "Barangay loading error:",
                err
            );

            setBarangays([]);

            if (err.response) {
                console.error(
                    "Server response:",
                    err.response.data
                );

                setError(
                    "Unable to load barangays. Please check the server."
                );
            } else {
                setError(
                    "Unable to connect to the server. Please make sure Django is running."
                );
            }

        } finally {
            setBarangayLoading(false);
        }
    };

    // =========================================================
    // HANDLE INPUT
    // =========================================================

    const handleChange = (e) => {
        const { name, value } = e.target;

        setFormData((prev) => ({
            ...prev,
            [name]: value,
        }));

        setError("");
    };

    // =========================================================
    // GET BARANGAY NAME
    // =========================================================

    const getBarangayName = (
        barangayId = formData.brgy
    ) => {
        const selected = barangays.find(
            (barangay) =>
                String(barangay.id) === String(barangayId)
        );

        return selected
            ? selected.name
            : "";
    };

    // =========================================================
    // VALIDATE FORM
    // =========================================================

    const validateForm = () => {
        if (!formData.lastname.trim()) {
            setError("Last name is required.");
            return false;
        }

        if (!formData.firstname.trim()) {
            setError("First name is required.");
            return false;
        }

        if (!formData.middlename.trim()) {
            setError("Middle name is required.");
            return false;
        }

        if (!formData.age) {
            setError("Age is required.");
            return false;
        }

        if (Number(formData.age) <= 0) {
            setError("Please enter a valid age.");
            return false;
        }

        if (!formData.sex) {
            setError("Please select your sex.");
            return false;
        }

        if (!formData.birthdate) {
            setError("Birthdate is required.");
            return false;
        }

        if (!formData.birthplace.trim()) {
            setError("Birthplace is required.");
            return false;
        }

        if (!formData.brgy) {
            setError("Please select a barangay.");
            return false;
        }

        if (!formData.phone.trim()) {
            setError("Phone number is required.");
            return false;
        }

        if (!/^09\d{9}$/.test(formData.phone)) {
            setError(
                "Phone number must contain exactly 11 digits and begin with 09."
            );
            return false;
        }

        if (!formData.email.trim()) {
            setError("Email address is required.");
            return false;
        }

        if (!formData.father.trim()) {
            setError("Father's name is required.");
            return false;
        }

        if (!formData.mother.trim()) {
            setError("Mother's name is required.");
            return false;
        }

        return true;
    };

    // =========================================================
    // PROCEED TO REVIEW
    // =========================================================

    const handleReview = () => {
        setError("");

        if (!validateForm()) {
            return;
        }

        setStep(2);

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    };

    // =========================================================
    // BACK TO FORM
    // =========================================================

    const handleBack = () => {
        setError("");
        setStep(1);

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    };

    // =========================================================
    // SUBMIT REGISTRATION
    // =========================================================

    const handleSubmit = async () => {
        setError("");

        if (!validateForm()) {
            setStep(1);

            window.scrollTo({
                top: 0,
                behavior: "smooth",
            });

            return;
        }

        setLoading(true);

        try {
            const payload = {
                ...formData,

                // Always NEW registration
                application_type: "NEW",

                // Convert age to number
                age: Number(formData.age),

                // Send barangay ID
                brgy: formData.brgy,
            };

            console.log(
                "Submitting registration:",
                payload
            );

            const response = await axios.post(
                REGISTRATION_API,
                payload,
                {
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                }
            );

            console.log(
                "Registration API response:",
                response.data
            );

            // =================================================
            // SUCCESS
            // =================================================

            if (response.data.success) {
                /*
                 * Use applicant returned by Django
                 * if available.
                 *
                 * Otherwise create applicant data
                 * from the submitted form.
                 */

                const applicant =
                    response.data.applicant || {
                        id:
                            response.data
                                .applicant_id,

                        applicant_id:
                            response.data
                                .applicant_id,

                        lastname:
                            formData.lastname,

                        firstname:
                            formData.firstname,

                        middlename:
                            formData.middlename,

                        age:
                            Number(
                                formData.age
                            ),

                        sex:
                            formData.sex,

                        birthdate:
                            formData.birthdate,

                        birthplace:
                            formData.birthplace,

                        brgy:
                            formData.brgy,

                        brgy_name:
                            getBarangayName(),

                        municipality:
                            formData.municipality,

                        province:
                            formData.province,

                        phone:
                            formData.phone,

                        email:
                            formData.email,

                        pwd_status:
                            formData.pwd_status,

                        citizenship_status:
                            formData.citizenship_status,

                        father:
                            formData.father,

                        mother:
                            formData.mother,

                        application_type:
                            "NEW",

                        status:
                            response.data
                                .status ||
                            "PENDING",

                        verification_status:
                            response.data
                                .verification_status ||
                            "UNVERIFIED",

                        is_senior:
                            response.data
                                .is_senior ??
                            Number(
                                formData.age
                            ) >= 60,
                    };

                console.log(
                    "Submitted applicant:",
                    applicant
                );

                setSubmittedApplicant(
                    applicant
                );

                setStep(3);

                window.scrollTo({
                    top: 0,
                    behavior: "smooth",
                });

                return;
            }

            // =================================================
            // API FAILURE
            // =================================================

            setError(
                response.data.error ||
                    response.data.message ||
                    "Registration failed."
            );

        } catch (err) {
            console.error(
                "Registration error:",
                err
            );

            // =================================================
            // DJANGO ERROR
            // =================================================

            if (err.response?.data?.error) {
                setError(
                    err.response.data.error
                );

            } else if (
                err.response?.data?.detail
            ) {
                setError(
                    err.response.data.detail
                );

            } else if (
                err.response?.data
            ) {
                const data =
                    err.response.data;

                if (
                    typeof data ===
                    "object"
                ) {
                    const firstError =
                        Object.values(data)
                            .flat()
                            .find(
                                (message) =>
                                    typeof message ===
                                    "string"
                            );

                    setError(
                        firstError ||
                            "Unable to submit registration."
                    );

                } else {
                    setError(
                        "Unable to submit registration."
                    );
                }

            } else {
                setError(
                    "Unable to connect to the server. Please try again."
                );
            }

        } finally {
            setLoading(false);
        }
    };

    // =========================================================
    // REGISTER ANOTHER APPLICANT
    // =========================================================

    const handleRegisterAnother = () => {
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
            pwd_status: "NO",
            citizenship_status: "BY_BIRTH",
            father: "",
            mother: "",
        });

        setSubmittedApplicant(null);
        setError("");
        setLoading(false);

        setStep(1);

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    };

    // =========================================================
    // DISPLAY VALUE
    // =========================================================

    const displayValue = (
        value,
        fallback = "Not provided"
    ) => {
        return value || fallback;
    };

    // =========================================================
    // DISPLAY SEX
    // =========================================================

    const getSexDisplay = (value) => {
        if (value === "MALE") {
            return "Male";
        }

        if (value === "FEMALE") {
            return "Female";
        }

        return displayValue(value);
    };

    // =========================================================
    // DISPLAY PWD
    // =========================================================

    const getPwdDisplay = (value) => {
        const values = {
            NO: "Not PWD",
            VISUAL: "Visual Disability",
            HEARING: "Hearing Disability",
            PHYSICAL: "Physical Disability",
            INTELLECTUAL:
                "Intellectual Disability",
            PSYCHOSOCIAL:
                "Psychosocial Disability",
            MULTIPLE:
                "Multiple Disabilities",
            OTHER: "Other",
        };

        return (
            values[value] ||
            displayValue(value)
        );
    };

    // =========================================================
    // DISPLAY CITIZENSHIP
    // =========================================================

    const getCitizenshipDisplay = (
        value
    ) => {
        const values = {
            BY_BIRTH: "By Birth",
            NATURALIZED: "Naturalized",
        };

        return (
            values[value] ||
            displayValue(value)
        );
    };

    // =========================================================
    // DISPLAY STATUS
    // =========================================================

    const getStatusDisplay = (value) => {
        const values = {
            PENDING: "Pending",
            APPROVED: "Approved",
            DISAPPROVED: "Disapproved",
            REVIEW: "Review",
        };

        return (
            values[value] ||
            "Pending"
        );
    };

    // =========================================================
    // FORM
    // =========================================================

    const renderForm = () => {
        return (
            <div className="registration-card">

                <div className="section-header">
                    <div className="section-number">
                        1
                    </div>

                    <div>
                        <h2>
                            Personal Information
                        </h2>

                        <p>
                            Enter the applicant's
                            personal details.
                        </p>
                    </div>
                </div>

                <div className="form-grid">

                    <div className="form-group">
                        <label>
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
                            placeholder="Enter last name"
                        />
                    </div>

                    <div className="form-group">
                        <label>
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
                            placeholder="Enter first name"
                        />
                    </div>

                    <div className="form-group">
                        <label>
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
                            placeholder="Enter middle name"
                        />
                    </div>

                    <div className="form-group">
                        <label>
                            Age
                            <span>*</span>
                        </label>

                        <input
                            type="number"
                            name="age"
                            value={
                                formData.age
                            }
                            onChange={
                                handleChange
                            }
                            min="1"
                            placeholder="Age"
                        />
                    </div>

                    <div className="form-group">
                        <label>
                            Sex
                            <span>*</span>
                        </label>

                        <select
                            name="sex"
                            value={
                                formData.sex
                            }
                            onChange={
                                handleChange
                            }
                        >
                            <option value="">
                                Select sex
                            </option>

                            <option value="MALE">
                                Male
                            </option>

                            <option value="FEMALE">
                                Female
                            </option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label>
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
                        />
                    </div>

                    <div className="form-group full-width">
                        <label>
                            Birthplace
                            <span>*</span>
                        </label>

                        <input
                            type="text"
                            name="birthplace"
                            value={
                                formData.birthplace
                            }
                            onChange={
                                handleChange
                            }
                            placeholder="Enter birthplace"
                        />
                    </div>

                </div>

                {/* ADDRESS */}

                <div className="subsection">

                    <div className="subsection-title">

                        <div className="subsection-icon">
                            A
                        </div>

                        <div>
                            <h3>
                                Residential Address
                            </h3>

                            <p>
                                Current residential
                                information
                            </p>
                        </div>

                    </div>

                    <div className="form-grid">

                        <div className="form-group full-width">

                            <label>
                                Barangay
                                <span>*</span>
                            </label>

                            <select
                                name="brgy"
                                value={
                                    formData.brgy
                                }
                                onChange={
                                    handleChange
                                }
                                disabled={
                                    barangayLoading
                                }
                            >
                                <option value="">
                                    {barangayLoading
                                        ? "Loading barangays..."
                                        : "Select barangay"}
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

                            {!barangayLoading &&
                                barangays.length ===
                                    0 && (
                                    <small
                                        style={{
                                            color:
                                                "#b42318",
                                            display:
                                                "block",
                                            marginTop:
                                                "6px",
                                        }}
                                    >
                                        No barangays
                                        available.
                                    </small>
                                )}

                        </div>

                        <div className="form-group">

                            <label>
                                Municipality
                            </label>

                            <input
                                type="text"
                                name="municipality"
                                value={
                                    formData.municipality
                                }
                                readOnly
                            />

                        </div>

                        <div className="form-group">

                            <label>
                                Province
                            </label>

                            <input
                                type="text"
                                name="province"
                                value={
                                    formData.province
                                }
                                readOnly
                            />

                        </div>

                    </div>

                </div>

                {/* CONTACT */}

                <div className="subsection">

                    <div className="subsection-title">

                        <div className="subsection-icon">
                            B
                        </div>

                        <div>
                            <h3>
                                Contact Information
                            </h3>

                            <p>
                                Provide your current
                                contact details
                            </p>
                        </div>

                    </div>

                    <div className="form-grid">

                        <div className="form-group">

                            <label>
                                Phone Number
                                <span>*</span>
                            </label>

                            <input
                                type="text"
                                name="phone"
                                value={
                                    formData.phone
                                }
                                onChange={(e) => {
                                    const value =
                                        e.target.value
                                            .replace(
                                                /\D/g,
                                                ""
                                            )
                                            .slice(
                                                0,
                                                11
                                            );

                                    setFormData(
                                        (prev) => ({
                                            ...prev,
                                            phone:
                                                value,
                                        })
                                    );

                                    setError("");
                                }}
                                maxLength={11}
                                placeholder="09XXXXXXXXX"
                            />

                        </div>

                        <div className="form-group">

                            <label>
                                Email Address
                                <span>*</span>
                            </label>

                            <input
                                type="email"
                                name="email"
                                value={
                                    formData.email
                                }
                                onChange={
                                    handleChange
                                }
                                placeholder="example@email.com"
                            />

                        </div>

                    </div>

                </div>

                {/* ADDITIONAL INFORMATION */}

                <div className="subsection">

                    <div className="subsection-title">

                        <div className="subsection-icon">
                            C
                        </div>

                        <div>
                            <h3>
                                Additional Information
                            </h3>

                            <p>
                                Citizenship and
                                disability information
                            </p>
                        </div>

                    </div>

                    <div className="form-grid">

                        <div className="form-group">

                            <label>
                                Citizenship
                            </label>

                            <select
                                name="citizenship_status"
                                value={
                                    formData.citizenship_status
                                }
                                onChange={
                                    handleChange
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

                        <div className="form-group">

                            <label>
                                PWD Status
                            </label>

                            <select
                                name="pwd_status"
                                value={
                                    formData.pwd_status
                                }
                                onChange={
                                    handleChange
                                }
                            >
                                <option value="NO">
                                    Not PWD
                                </option>

                                <option value="VISUAL">
                                    Visual Disability
                                </option>

                                <option value="HEARING">
                                    Hearing Disability
                                </option>

                                <option value="PHYSICAL">
                                    Physical Disability
                                </option>

                                <option value="INTELLECTUAL">
                                    Intellectual Disability
                                </option>

                                <option value="PSYCHOSOCIAL">
                                    Psychosocial Disability
                                </option>

                                <option value="MULTIPLE">
                                    Multiple Disabilities
                                </option>

                                <option value="OTHER">
                                    Other
                                </option>
                            </select>

                        </div>

                    </div>

                </div>

                {/* PARENTS */}

                <div className="subsection">

                    <div className="subsection-title">

                        <div className="subsection-icon">
                            D
                        </div>

                        <div>
                            <h3>
                                Parent Information
                            </h3>

                            <p>
                                Provide the names of
                                your parents
                            </p>
                        </div>

                    </div>

                    <div className="form-grid">

                        <div className="form-group">

                            <label>
                                Father's Name
                                <span>*</span>
                            </label>

                            <input
                                type="text"
                                name="father"
                                value={
                                    formData.father
                                }
                                onChange={
                                    handleChange
                                }
                                placeholder="Enter father's name"
                            />

                        </div>

                        <div className="form-group">

                            <label>
                                Mother's Name
                                <span>*</span>
                            </label>

                            <input
                                type="text"
                                name="mother"
                                value={
                                    formData.mother
                                }
                                onChange={
                                    handleChange
                                }
                                placeholder="Enter mother's name"
                            />

                        </div>

                    </div>

                </div>

                {/* ERROR */}

                {error && (
                    <div className="registration-error">

                        <strong>
                            Unable to continue
                        </strong>

                        <span>
                            {error}
                        </span>

                    </div>
                )}

                {/* ACTIONS */}

                <div className="form-actions">

                    <button
                        type="button"
                        className="secondary-button"
                        onClick={() =>
                            navigate(-1)
                        }
                    >
                        Cancel
                    </button>

                    <button
                        type="button"
                        className="primary-button"
                        onClick={
                            handleReview
                        }
                        disabled={
                            barangayLoading
                        }
                    >
                        Review Information
                    </button>

                </div>

            </div>
        );
    };

    // =========================================================
    // REVIEW
    // =========================================================

    const renderReview = () => {
        return (
            <div className="registration-card review-card">

                <div className="review-heading">

                    <div className="review-check">
                        ✓
                    </div>

                    <div>
                        <h2>
                            Review Your Information
                        </h2>

                        <p>
                            Please carefully review
                            all information before
                            submitting your
                            registration.
                        </p>
                    </div>

                </div>

                <div className="review-notice">

                    <strong>
                        Important
                    </strong>

                    <span>
                        Make sure that all information
                        is correct. Once submitted,
                        your application will be
                        recorded as a New Registration
                        and placed under review.
                    </span>

                </div>

                {/* PERSONAL */}

                <div className="review-section">

                    <div className="review-section-header">

                        <h3>
                            Personal Information
                        </h3>

                        <button
                            type="button"
                            onClick={handleBack}
                        >
                            Edit
                        </button>

                    </div>

                    <div className="review-grid">

                        <ReviewItem
                            label="Last Name"
                            value={
                                formData.lastname
                            }
                        />

                        <ReviewItem
                            label="First Name"
                            value={
                                formData.firstname
                            }
                        />

                        <ReviewItem
                            label="Middle Name"
                            value={
                                formData.middlename
                            }
                        />

                        <ReviewItem
                            label="Age"
                            value={
                                formData.age
                            }
                        />

                        <ReviewItem
                            label="Sex"
                            value={getSexDisplay(
                                formData.sex
                            )}
                        />

                        <ReviewItem
                            label="Birthdate"
                            value={
                                formData.birthdate
                            }
                        />

                        <ReviewItem
                            label="Birthplace"
                            value={
                                formData.birthplace
                            }
                            full
                        />

                    </div>

                </div>

                {/* ADDRESS */}

                <div className="review-section">

                    <div className="review-section-header">

                        <h3>
                            Residential Address
                        </h3>

                        <button
                            type="button"
                            onClick={handleBack}
                        >
                            Edit
                        </button>

                    </div>

                    <div className="review-grid">

                        <ReviewItem
                            label="Barangay"
                            value={
                                getBarangayName()
                            }
                        />

                        <ReviewItem
                            label="Municipality"
                            value={
                                formData.municipality
                            }
                        />

                        <ReviewItem
                            label="Province"
                            value={
                                formData.province
                            }
                        />

                    </div>

                </div>

                {/* CONTACT */}

                <div className="review-section">

                    <div className="review-section-header">

                        <h3>
                            Contact Information
                        </h3>

                        <button
                            type="button"
                            onClick={handleBack}
                        >
                            Edit
                        </button>

                    </div>

                    <div className="review-grid">

                        <ReviewItem
                            label="Phone Number"
                            value={
                                formData.phone
                            }
                        />

                        <ReviewItem
                            label="Email Address"
                            value={
                                formData.email
                            }
                        />

                    </div>

                </div>

                {/* ADDITIONAL */}

                <div className="review-section">

                    <div className="review-section-header">

                        <h3>
                            Additional Information
                        </h3>

                        <button
                            type="button"
                            onClick={handleBack}
                        >
                            Edit
                        </button>

                    </div>

                    <div className="review-grid">

                        <ReviewItem
                            label="Citizenship"
                            value={getCitizenshipDisplay(
                                formData.citizenship_status
                            )}
                        />

                        <ReviewItem
                            label="PWD Status"
                            value={getPwdDisplay(
                                formData.pwd_status
                            )}
                        />

                    </div>

                </div>

                {/* PARENTS */}

                <div className="review-section">

                    <div className="review-section-header">

                        <h3>
                            Parent Information
                        </h3>

                        <button
                            type="button"
                            onClick={handleBack}
                        >
                            Edit
                        </button>

                    </div>

                    <div className="review-grid">

                        <ReviewItem
                            label="Father's Name"
                            value={
                                formData.father
                            }
                        />

                        <ReviewItem
                            label="Mother's Name"
                            value={
                                formData.mother
                            }
                        />

                    </div>

                </div>

                {/* APPLICATION SUMMARY */}

                <div className="application-summary">

                    <div>
                        <span>
                            Application Type
                        </span>

                        <strong>
                            New Registration
                        </strong>
                    </div>

                    <div>
                        <span>
                            Initial Status
                        </span>

                        <strong>
                            Pending
                        </strong>
                    </div>

                    <div>
                        <span>
                            Verification
                        </span>

                        <strong>
                            Unverified
                        </strong>
                    </div>

                </div>

                {error && (
                    <div className="registration-error">

                        <strong>
                            Unable to submit
                        </strong>

                        <span>
                            {error}
                        </span>

                    </div>
                )}

                {/* FINAL ACTIONS */}

                <div className="form-actions">

                    <button
                        type="button"
                        className="secondary-button"
                        onClick={
                            handleBack
                        }
                        disabled={loading}
                    >
                        Back to Edit
                    </button>

                    <button
                        type="button"
                        className="primary-button confirm-button"
                        onClick={
                            handleSubmit
                        }
                        disabled={loading}
                    >
                        {loading
                            ? "Submitting Registration..."
                            : "Confirm & Submit"}
                    </button>

                </div>

            </div>
        );
    };

    // =========================================================
    // SUCCESS
    // =========================================================

    const renderSuccess = () => {
        const applicant =
            submittedApplicant ||
            formData;

        const barangayName =
            applicant.brgy_name ||
            getBarangayName(
                applicant.brgy
            );

        const status =
            applicant.status ||
            "PENDING";

        const senior =
            applicant.is_senior ??
            Number(applicant.age) >= 60;

        return (
            <div className="success-page">

                <div className="success-page-header">

                    <h1>
                        Registration Successful
                    </h1>

                    <p>
                        The applicant has been
                        successfully registered.
                    </p>

                </div>

                <div className="success-card">

                    <div className="success-card-header">

                        <div className="success-heading">

                            <div className="success-icon">
                                ✓
                            </div>

                            <div>

                                <h2>
                                    Registration
                                    Successfully
                                    Submitted
                                </h2>

                                <p>
                                    Please keep the
                                    following information
                                    for your records.
                                </p>

                            </div>

                        </div>

                    </div>

                    <div className="success-card-body">

                        {/* APPLICATION */}

                        <div className="success-section">

                            <h3>
                                Application Information
                            </h3>

                            <div className="success-grid">

                                <div className="success-detail">

                                    <span>
                                        Application Type
                                    </span>

                                    <strong>
                                        New Registration
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Status
                                    </span>

                                    <strong>
                                        <span className="success-status">
                                            {getStatusDisplay(
                                                status
                                            )}
                                        </span>
                                    </strong>

                                </div>

                            </div>

                        </div>

                        {/* APPLICANT */}

                        <div className="success-section">

                            <h3>
                                Applicant Information
                            </h3>

                            <div className="success-grid">

                                <div className="success-detail success-detail-full">

                                    <span>
                                        Name
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.lastname
                                            )
                                        }
                                        ,{" "}
                                        {
                                            displayValue(
                                                applicant.firstname
                                            )
                                        }{" "}
                                        {
                                            displayValue(
                                                applicant.middlename
                                            )
                                        }
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Age
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.age
                                            )
                                        }
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Sex
                                    </span>

                                    <strong>
                                        {getSexDisplay(
                                            applicant.sex
                                        )}
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Birthdate
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.birthdate
                                            )
                                        }
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Birthplace
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.birthplace
                                            )
                                        }
                                    </strong>

                                </div>

                            </div>

                        </div>

                        {/* ADDRESS */}

                        <div className="success-section">

                            <h3>
                                Address
                            </h3>

                            <div className="success-grid">

                                <div className="success-detail">

                                    <span>
                                        Barangay
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                barangayName
                                            )
                                        }
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Municipality
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.municipality,
                                                "Pio Duran"
                                            )
                                        }
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Province
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.province,
                                                "Albay"
                                            )
                                        }
                                    </strong>

                                </div>

                            </div>

                        </div>

                        {/* CONTACT */}

                        <div className="success-section">

                            <h3>
                                Contact Information
                            </h3>

                            <div className="success-grid">

                                <div className="success-detail">

                                    <span>
                                        Phone
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.phone
                                            )
                                        }
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Email
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.email
                                            )
                                        }
                                    </strong>

                                </div>

                            </div>

                        </div>

                        {/* OTHER */}

                        <div className="success-section">

                            <h3>
                                Other Information
                            </h3>

                            <div className="success-grid">

                                <div className="success-detail">

                                    <span>
                                        PWD Status
                                    </span>

                                    <strong>
                                        {getPwdDisplay(
                                            applicant.pwd_status
                                        )}
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Citizenship
                                    </span>

                                    <strong>
                                        {getCitizenshipDisplay(
                                            applicant.citizenship_status
                                        )}
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Father's Name
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.father
                                            )
                                        }
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Mother's Name
                                    </span>

                                    <strong>
                                        {
                                            displayValue(
                                                applicant.mother
                                            )
                                        }
                                    </strong>

                                </div>

                                <div className="success-detail">

                                    <span>
                                        Senior Citizen
                                    </span>

                                    <strong>
                                        {senior
                                            ? "Yes"
                                            : "No"}
                                    </strong>

                                </div>

                            </div>

                        </div>

                        {/* NOTICE */}

                        <div className="success-notice">

                            <p>
                                Your application is
                                currently{" "}
                                <strong>
                                    {
                                        getStatusDisplay(
                                            status
                                        )
                                    }
                                </strong>.
                            </p>

                            <p>
                                Please keep this
                                information for your
                                reference.
                            </p>

                        </div>

                        {/* ACTION */}

                        <div className="success-actions">

                            <button
                                type="button"
                                className="success-register-button"
                                onClick={
                                    handleRegisterAnother
                                }
                            >
                                Register Another
                                Applicant
                            </button>

                        </div>

                    </div>

                </div>

            </div>
        );
    };

    // =========================================================
    // RETURN
    // =========================================================

    return (
        <div className="new-registration-page">

            <div className="registration-wrapper">

                {/* HEADER */}

                <div className="page-header">

                    <div className="header-icon">
                        NR
                    </div>

                    <div>

                        <div className="header-label">
                            GOVERNMENT ONLINE
                            REGISTRATION
                        </div>

                        <h1>
                            New Registration
                        </h1>

                        <p>
                            Complete your
                            registration information
                            and review it before
                            submission.
                        </p>

                    </div>

                </div>

                {/* STEPPER */}

                <div className="registration-stepper">

                    <div
                        className={
                            step >= 1
                                ? "step active"
                                : "step"
                        }
                    >
                        <div className="step-circle">
                            1
                        </div>

                        <span>
                            Information
                        </span>
                    </div>

                    <div
                        className={
                            step >= 2
                                ? "step-line active"
                                : "step-line"
                        }
                    />

                    <div
                        className={
                            step >= 2
                                ? "step active"
                                : "step"
                        }
                    >
                        <div className="step-circle">
                            2
                        </div>

                        <span>
                            Review
                        </span>
                    </div>

                    <div
                        className={
                            step >= 3
                                ? "step-line active"
                                : "step-line"
                        }
                    />

                    <div
                        className={
                            step >= 3
                                ? "step active"
                                : "step"
                        }
                    >
                        <div className="step-circle">
                            3
                        </div>

                        <span>
                            Submitted
                        </span>
                    </div>

                </div>

                {/* CONTENT */}

                {step === 1 &&
                    renderForm()}

                {step === 2 &&
                    renderReview()}

                {step === 3 &&
                    renderSuccess()}

            </div>

        </div>
    );
}

// =============================================================
// REVIEW ITEM
// =============================================================

function ReviewItem({
    label,
    value,
    full = false,
}) {
    return (
        <div
            className={
                full
                    ? "review-item full"
                    : "review-item"
            }
        >
            <span>
                {label}
            </span>

            <strong>
                {value || "Not provided"}
            </strong>
        </div>
    );
}

export default NewRegistration;