import { Route, Routes } from "react-router-dom";
import ApplicationPack from "./screens/ApplicationPack";
import BenefitsFound from "./screens/BenefitsFound";
import BillCheckResult from "./screens/BillCheckResult";
import CaseworkerCard from "./screens/CaseworkerCard";
import Home from "./screens/Home";
import LanguagePicker from "./screens/LanguagePicker";
import LetterResult from "./screens/LetterResult";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LanguagePicker />} />
      <Route path="/home" element={<Home />} />
      <Route path="/letter-result" element={<LetterResult />} />
      <Route path="/benefits" element={<BenefitsFound />} />
      <Route path="/application-pack" element={<ApplicationPack />} />
      <Route path="/caseworker-card" element={<CaseworkerCard />} />
      <Route path="/bill-check" element={<BillCheckResult />} />
    </Routes>
  );
}
