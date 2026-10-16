import { Navigate, Route, Routes } from "react-router";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import PrivacyPage from "./pages/PrivacyPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import SavedPage from "./pages/SavedPage";
import SharedTripPage from "./pages/SharedTripPage";
import TripPage from "./pages/TripPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/trip" element={<TripPage />} />
      <Route path="/trip/:id" element={<SharedTripPage />} />
      <Route path="/saved" element={<SavedPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
