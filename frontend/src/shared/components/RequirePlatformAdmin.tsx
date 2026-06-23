import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "@auth/useAuth";
import { LoadingFullPage } from "@shared/components/LoadingFullPage";

/**
 * Route guard for the platform-admin console. Assumes it renders inside
 * `RequireAuth` (so a user is present); redirects non-admins to the dashboard
 * home rather than leaking the existence of admin routes.
 */
export function RequirePlatformAdmin({ children }: Readonly<{ children: ReactNode }>) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingFullPage />;
  }
  if (!user?.is_platform_admin) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
