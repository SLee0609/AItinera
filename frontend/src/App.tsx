import { Navigate, Route, Routes } from "react-router";
import LandingPage from "./pages/LandingPage";
import TripPage from "./pages/TripPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/trip" element={<TripPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
