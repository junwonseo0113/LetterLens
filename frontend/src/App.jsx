import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import BottomTabBar from "./components/BottomTabBar";
import { useAuth } from "./context/AuthContext";
import ApplicationPack from "./screens/ApplicationPack";
import Apply from "./screens/Apply";
import ApplyReview from "./screens/ApplyReview";
import ApplyStatus from "./screens/ApplyStatus";
import BenefitsFound from "./screens/BenefitsFound";
import BillCheckResult from "./screens/BillCheckResult";
import CaseworkerCard from "./screens/CaseworkerCard";
import CaseworkerQueue from "./screens/CaseworkerQueue";
import Home from "./screens/Home";
import LanguagePicker from "./screens/LanguagePicker";
import LetterResult from "./screens/LetterResult";
import SignIn from "./screens/SignIn";

const NO_TAB_BAR = new Set(["/", "/sign-in", "/caseworker"]);

const PROTECTED_ROUTES = [
  { path: "/home", Screen: Home },
  { path: "/letter-result", Screen: LetterResult },
  { path: "/benefits", Screen: BenefitsFound },
  { path: "/application-pack", Screen: ApplicationPack },
  { path: "/caseworker-card", Screen: CaseworkerCard },
  { path: "/bill-check", Screen: BillCheckResult },
  { path: "/apply", Screen: Apply },
  { path: "/apply/review", Screen: ApplyReview },
  { path: "/apply/status", Screen: ApplyStatus },
];

// Letters and applications belong to a verified person -- sign in first.
function RequireAuth({ children }) {
  const { token } = useAuth();
  const location = useLocation();
  if (!token) return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  return children;
}

export default function App() {
  const location = useLocation();
  const { token } = useAuth();
  const showTabBar = token && !NO_TAB_BAR.has(location.pathname);

  return (
    <>
      <Routes>
        <Route path="/" element={<LanguagePicker />} />
        <Route path="/sign-in" element={<SignIn />} />
        <Route path="/caseworker" element={<CaseworkerQueue />} />
        {PROTECTED_ROUTES.map(({ path, Screen }) => (
          <Route
            key={path}
            path={path}
            element={
              <RequireAuth>
                <Screen />
              </RequireAuth>
            }
          />
        ))}
      </Routes>
      {showTabBar && <BottomTabBar />}
    </>
  );
}
