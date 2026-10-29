import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { SiteFooter } from "../../pages/public/PublicLayout";
import { api } from "../../services/api";
import { VerifyBanner } from "../VerifyBanner";
import { AppHeader } from "./AppHeader";
import { BottomNav } from "./BottomNav";

/** Frame of every signed-in page. */
export function AppLayout() {
  const location = useLocation();

  useEffect(() => {
    api.pageView(location.pathname).catch(() => undefined); // admin traffic stats; never blocks the UI
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-canvas text-slate-900">
      <AppHeader />
      <VerifyBanner />
      <main className="mx-auto max-w-7xl px-4 pt-6 pb-12 sm:px-6">
        <Outlet />
      </main>
      {/* Below lg the bottom navigation bar covers the last 4rem: keep the footer clear of it. */}
      <div className="pb-16 lg:pb-0">
        <SiteFooter />
      </div>
      <BottomNav />
    </div>
  );
}
