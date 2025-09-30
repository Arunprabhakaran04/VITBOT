import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useStore } from '@/lib/store';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: 'admin' | 'user';
}

export const ProtectedRoute = ({ children, requiredRole }: ProtectedRouteProps) => {
  const { user } = useStore();

  // Redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/" replace />;
  }

  // Check role requirement
  if (requiredRole && user.role !== requiredRole) {
    // Admin trying to access user route or user trying to access admin route
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};