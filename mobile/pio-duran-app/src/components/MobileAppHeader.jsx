import { useLayoutEffect, useRef } from "react";
import MobileHeader from "./MobileHeader";
import MobileNavigation from "./MobileNavigation";

export default function MobileAppHeader() {
    const header = useRef(null);
    const spacer = useRef(null);

    useLayoutEffect(() => {
        const updateHeight = () => {
            spacer.current.style.height = `${header.current.getBoundingClientRect().height}px`;
        };
        updateHeight();
        const observer = new ResizeObserver(updateHeight);
        observer.observe(header.current);
        return () => observer.disconnect();
    }, []);

    return (
        <>
            <div ref={header} className="mobile-fixed-header">
                <MobileHeader />
                <MobileNavigation />
            </div>
            <div ref={spacer} aria-hidden="true" />
        </>
    );
}
