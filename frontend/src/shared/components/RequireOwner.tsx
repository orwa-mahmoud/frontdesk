import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "@auth/useAuth";
import { LoadingFullPage } from "@shared/components/LoadingFullPage";

/**
 * Route guard for tenant-owner-only pages (settings, team). Assumes it renders
 * inside `RequireAuth`; redirects non-owners (STAFF) to the dashboard home.
 */
export function RequireOwner({ children }: Readonly<{ children: ReactNode }>) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingFullPage />;
  }
  if (user?.tenant.role !== "owner") {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
