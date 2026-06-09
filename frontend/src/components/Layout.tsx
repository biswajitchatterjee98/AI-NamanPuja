import { Link, useLocation } from "react-router-dom";

type Props = {
  children: React.ReactNode;
};

export default function Layout({ children }: Props) {
  const location = useLocation();
  const isHome = location.pathname === "/";

  return (
    <div className="app-shell">
      <div className="bg-glow bg-glow-top" aria-hidden />
      <div className="bg-glow bg-glow-bottom" aria-hidden />
      <div className="bg-pattern" aria-hidden />

      <header className="topbar">
        <div className="topbar-ornament" aria-hidden />
        <div className="topbar-inner">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden>
              <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                <ellipse cx="18" cy="28" rx="10" ry="3" fill="#E8841A" opacity="0.35" />
                <path d="M18 8c-1 4-4 8-4 12a4 4 0 008 0c0-4-3-8-4-12z" fill="#F59E0B" />
                <path d="M18 6v3M14 7l1 2M22 7l-1 2" stroke="#D97706" strokeWidth="1.2" strokeLinecap="round" />
                <ellipse cx="18" cy="20" rx="2.5" ry="3" fill="#FDE68A" opacity="0.9" />
              </svg>
            </span>
            <div>
              <span className="brand-name">NamanPuja</span>
              <span className="brand-tag">Content Studio</span>
            </div>
          </Link>
          <nav className="topnav">
            <Link to="/" className={`nav-link${isHome ? " active" : ""}`}>
              Dashboard
            </Link>
          </nav>
        </div>
      </header>

      <main className="main-content">{children}</main>

      <footer className="footer">
        <span className="footer-ornament" aria-hidden>✦</span>
        <span>Generate · Review · Publish</span>
        <span className="footer-ornament" aria-hidden>✦</span>
      </footer>
    </div>
  );
}
