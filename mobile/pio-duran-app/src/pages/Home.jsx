import { Link } from "react-router-dom";

const applications = [
    { title: "APPLICATION FOR NEW REGISTRATION", route: "/new-registration", icon: "new" },
    { title: "APPLICATION FOR CHANGE OF NAME/CORRECTION", route: "/update-information", icon: "edit" },
    { title: "APPLICATION FOR TRANSFER", route: "/transfer", icon: "transfer" },
    { title: "APPLICATION FOR REACTIVATION", route: "/reactivation", icon: "reactivate" },
    { title: "APPLICATION FOR INCLUSION/REINSTATEMENT", route: "/reinstatement", icon: "restore" },
];

function ServiceIcon({ kind }) {
    const paths = {
        new: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M20 8v6m-3-3h6" /></>,
        edit: <><path d="m16 3 5 5-12 12-6 1 1-6L16 3Z" /><path d="m13 6 5 5" /></>,
        transfer: <path d="M3 7h17m-5-5 5 5-5 5M21 17H4m5-5-5 5 5 5" />,
        reactivate: <><path d="M3 11a9 9 0 1 1 2 7M3 4v7h7" /><path d="M12 7v5l3 2" /></>,
        restore: <path d="M9 14 4 9l5-5M4 9h10a7 7 0 0 1 0 14" />,
    };
    return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[kind]}</svg>;
}

export default function Home() {
    return (
        <div className="verify-page mobile-home">

            <main className="verify-main" id="main-content">
                <div className="verify-container">
                    <div className="mobile-home-intro">
                        <span className="mobile-eyebrow">APPLICANT SERVICES</span>
                        <h2>Your registration,<br />one step closer.</h2>
                        <p>Choose a service below. Keep your personal details and supporting documents ready.</p>
                    </div>
                    <section className="mobile-application-menu" aria-labelledby="application-menu-heading">
                    <h2 id="application-menu-heading">SELECT AN APPLICATION TYPE</h2>
                    <nav className="home-services" aria-label="Application services">
                        {applications.map(application => (
                            <Link key={application.route} to={application.route} className="service-card">
                                <span className="mobile-service-icon"><ServiceIcon kind={application.icon} /></span>
                                <div className="service-card-content"><h3>{application.title}</h3></div>
                                <svg className="mobile-service-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 12h16m-5-5 5 5-5 5" /></svg>
                            </Link>
                        ))}
                    </nav>
                    </section>
                </div>
            </main>
        </div>
    );
}
