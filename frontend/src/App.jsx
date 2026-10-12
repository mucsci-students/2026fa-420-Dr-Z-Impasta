import { Outlet } from "react-router";
import { IN_BROWSER } from "./api/backend.js";
import BrowserSession from "./layout/BrowserSession.jsx";
import ConnectionBanner from "./layout/ConnectionBanner.jsx";
import Header from "./layout/Header.jsx";
import AppStateProvider from "./state/AppStateProvider.jsx";
import ToastProvider from "./state/ToastProvider.jsx";

/** The frame around every mode: shared state, notifications, header, and the current page. */
export default function App() {
  return (
    <AppStateProvider>
      <ToastProvider>
        <div className="app">
          <Header />
          <ConnectionBanner />
          {IN_BROWSER && <BrowserSession />}
          <main className="page" id="main">
            <Outlet />
          </main>
        </div>
      </ToastProvider>
    </AppStateProvider>
  );
}
