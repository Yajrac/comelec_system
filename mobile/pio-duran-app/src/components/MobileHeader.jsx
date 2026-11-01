import ConnectionStatus from "./ConnectionStatus";

export default function MobileHeader({ title }) {
    return (
        <header className="government-header mobile-brand-header">
            <div className="government-header-inner">
                <div className="government-logo"><img src="/images/comelec.png" alt="Commission on Elections seal" /></div>
                <div><p className="mobile-brand-eyebrow">COMMISSION ON ELECTIONS</p><h1 className="government-title">Pio Duran</h1><p className="government-subtitle">Registration &amp; Applicant Services</p></div>
                <ConnectionStatus />
            </div>
            {title && <div className="mobile-screen-heading"><h2>{title}</h2></div>}
        </header>
    );
}
