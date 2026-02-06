import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ArmyProvider } from "./context/ArmyContext";
import { Toaster } from "./components/ui/sonner";
import GameSelection from "./pages/GameSelection";
import ArmyBuilder from "./pages/ArmyBuilder";

function App() {
  return (
    <ArmyProvider>
      <div className="min-h-screen bg-[#2e2f2b]">
        <Toaster position="top-right" richColors theme="dark" />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<GameSelection />} />
            <Route path="/builder" element={<ArmyBuilder />} />
          </Routes>
        </BrowserRouter>
      </div>
    </ArmyProvider>
  );
}

export default App;
