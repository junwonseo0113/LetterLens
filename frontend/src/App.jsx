import { Route, Routes, useLocation } from "react-router-dom";
import BottomTabBar from "./components/BottomTabBar";
import ApplicationPack from "./screens/ApplicationPack";
import BenefitsFound from "./screens/BenefitsFound";
import BillCheckResult from "./screens/BillCheckResult";
import CaseworkerCard from "./screens/CaseworkerCard";
import Home from "./screens/Home";
import LanguagePicker from "./screens/LanguagePicker";
import LetterResult from "./screens/LetterResult";

export default function App() {
  const location = useLocation();
  const showTabBar = location.pathname !== "/";

  return (
    <>
      <Routes>
        <Route path="/" element={<LanguagePicker />} />
        <Route path="/home" element={<Home />} />
        <Route path="/letter-result" element={<LetterResult />} />
        <Route path="/benefits" element={<BenefitsFound />} />
        <Route path="/application-pack" element={<ApplicationPack />} />
        <Route path="/caseworker-card" element={<CaseworkerCard />} />
        <Route path="/bill-check" element={<BillCheckResult />} />
      </Routes>
      {showTabBar && <BottomTabBar />}
    </>
  );
}
