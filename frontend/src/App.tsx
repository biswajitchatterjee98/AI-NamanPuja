import { Link, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Review from "./pages/Review";

export default function App() {
  return (
    <div>
      <header className="container" style={{ paddingBottom: 0 }}>
        <h1 style={{ marginBottom: "0.25rem" }}>NamanPuja Content Pipeline</h1>
        <p style={{ marginTop: 0, color: "#6b5b4f" }}>AI batch generation, review, and upload</p>
        <nav style={{ marginBottom: "1rem" }}>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/batch/:batchId" element={<Review />} />
        </Routes>
      </main>
    </div>
  );
}
