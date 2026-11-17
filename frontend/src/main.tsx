import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { I18nProvider, useI18n } from "./i18n";
import "./index.css";
import About from "./pages/About";
import Dashboard from "./pages/Dashboard";
import HistoryPage from "./pages/History";
import Landing from "./pages/Landing";
import Results from "./pages/Results";
import Scanner from "./pages/Scanner";
import Status from "./pages/Status";

function NotFound() {
  const { t } = useI18n();
  return <div className="py-20 text-center text-slate-400">{t("common.notFoundPage")}</div>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/scan" element={<Scanner />} />
            <Route path="/results/:id" element={<Results />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/methodology" element={<About />} />
            <Route path="/status" element={<Status />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </I18nProvider>
  </React.StrictMode>,
);
