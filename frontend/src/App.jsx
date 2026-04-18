import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import AuthPage from "./pages/AuthPage";
import UploadPage from "./pages/UploadPage";
import CoachPage from "./pages/CoachPage";
import MetricsPage from "./pages/MetricsPage";

function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? children : <Navigate to="/auth" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/upload" element={<PrivateRoute><UploadPage /></PrivateRoute>} />
      <Route path="/coach" element={<PrivateRoute><CoachPage /></PrivateRoute>} />
      <Route path="/metrics" element={<PrivateRoute><MetricsPage /></PrivateRoute>} />
      <Route path="/" element={<Navigate to="/upload" replace />} />
    </Routes>
  );
}
