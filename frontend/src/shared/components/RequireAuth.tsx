import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@auth/useAuth";
import { LoadingFullPage } from "@shared/components/LoadingFullPage";

export function RequireAuth({ children }: Readonly<{ children: ReactNode }>) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingFullPage />;
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <>{children}</>;
}
