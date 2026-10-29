
import React from "react";
import { useNavigate } from "react-router-dom";

const Home = () => {
    const navigate = useNavigate();

    const applications = [
        {
            title: "New Registration",
            description:
                "Apply for a new registration. Your existing registration status will be verified first.",
            route: "/verify-applicant",
        },
        {
            title: "Update Information",
            description:
                "Request changes or corrections to your existing applicant information.",
            route: "/update-information",
        },
        {
            title: "Transfer",
            description:
                "Request the transfer of your registration to another barangay or locality.",
            route: "/transfer",
        },
        {
            title: "Reactivation",
            description:
                "Request reactivation of an inactive registration.",
            route: "/reactivation",
        },
        {
            title: "Reinstatement",
            description:
                "Request reinstatement of a previously cancelled or inactive registration.",
            route: "/reinstatement",
        },
    ];

    const handleApplicationClick = (route) => {
        navigate(route);
    };

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
                        className="active"
                        onClick={() => navigate("/")}
                    >
                        Home
                    </button>

                </div>

            </nav>


            {/* =================================================
                MAIN CONTENT
            ================================================= */}

            <main className="verify-main">

                <div className="verify-container">

                    {/* =========================================
                        PAGE HEADER
                    ========================================= */}

                    <div className="page-header">

                        <h1>
                            Applicant Services
                        </h1>

                        <p>
                            Select the service you want to access.
                            New Registration requires applicant
                            verification before continuing.
                        </p>

                    </div>


                    {/* =========================================
                        APPLICATION SERVICES
                    ========================================= */}

                    <div className="home-services">

                        {applications.map((application) => (

                            <button
                                key={application.title}
                                type="button"
                                className="service-card"
                                onClick={() =>
                                    handleApplicationClick(
                                        application.route
                                    )
                                }
                            >

                                <div className="service-card-content">

                                    <h2>
                                        {application.title}
                                    </h2>

                                    <p>
                                        {application.description}
                                    </p>

                                </div>

                                <div className="service-card-arrow">
                                    →
                                </div>

                            </button>

                        ))}

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

export default Home;