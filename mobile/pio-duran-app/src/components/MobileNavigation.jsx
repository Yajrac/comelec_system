import { useLocation, useNavigate } from "react-router-dom";

export default function MobileNavigation() {
    const { pathname } = useLocation();
    const navigate = useNavigate();
    const isHome = pathname === "/";
    if (isHome) return null;

    function goBack() {
        if ((window.history.state?.idx ?? 0) > 0) navigate(-1);
        else navigate("/", { replace: true });
    }

    return (
        <nav className="mobile-top-nav" aria-label="App navigation">
            <button type="button" className="bottom-nav-item" onClick={goBack} disabled={isHome}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m12 5-7 7 7 7M5 12h15" /></svg>
                <span>Back</span>
            </button>
        </nav>
    );
}
