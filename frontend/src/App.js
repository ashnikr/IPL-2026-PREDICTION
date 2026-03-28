import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Predict from "./pages/Predict";
import Agents from "./pages/Agents";
import Dream11 from "./pages/Dream11";
import Live from "./pages/Live";
import Form from "./pages/Form";
import News from "./pages/News";
import H2H from "./pages/H2H";
import Strengths from "./pages/Strengths";
import Schedule from "./pages/Schedule";
import Squads from "./pages/Squads";
import Accuracy from "./pages/Accuracy";
import Pricing from "./pages/Pricing";
import Earn from "./pages/Earn";
import Payment from "./pages/Payment";

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="app">
        <button className="mobile-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
          &#9776;
        </button>
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/predict" element={<Predict />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/dream11" element={<Dream11 />} />
            <Route path="/live" element={<Live />} />
            <Route path="/form" element={<Form />} />
            <Route path="/news" element={<News />} />
            <Route path="/h2h" element={<H2H />} />
            <Route path="/strengths" element={<Strengths />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/squads" element={<Squads />} />
            <Route path="/accuracy" element={<Accuracy />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/earn" element={<Earn />} />
            <Route path="/payment" element={<Payment />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
