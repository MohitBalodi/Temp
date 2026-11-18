import { useQueryClient } from '@tanstack/react-query';
import { lazy, Suspense, useEffect } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';

import { SESSION_EXPIRED_EVENT } from '@/api/client';
import AppLayout from '@/components/AppLayout';
import ProtectedRoute from '@/components/ProtectedRoute';
import { Toaster } from '@/components/ui/toaster';
import Certificates from '@/pages/Certificates';
import Dashboard from '@/pages/Dashboard';
import ImportCertificates from '@/pages/ImportCertificates';
import AuditLog from '@/pages/AuditLog';
import Institutions from '@/pages/Institutions';
import Login from '@/pages/Login';
import MyVerifications from '@/pages/MyVerifications';
import RequestDetail from '@/pages/RequestDetail';
import Requests from '@/pages/Requests';
import VerificationDetail from '@/pages/VerificationDetail';

// Lazy-loaded since the live QR scanner lived here; the page is small now
// that it does not, but splitting a route only verifiers reach still costs
// nothing and keeps the main bundle to what every role needs.
const Verify = lazy(() => import('@/pages/Verify'));

export default function App() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    const onExpired = () => {
      queryClient.clear();
      navigate('/login', { replace: true });
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, [navigate, queryClient]);

  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route element={<ProtectedRoute roles={['institution', 'admin']} />}>
              <Route path="/certificates" element={<Certificates />} />
            </Route>
            <Route element={<ProtectedRoute roles={['institution']} />}>
              <Route path="/certificates/import" element={<ImportCertificates />} />
            </Route>
            <Route element={<ProtectedRoute roles={['verifier', 'admin']} />}>
              <Route
                path="/verify"
                element={
                  <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
                    <Verify />
                  </Suspense>
                }
              />
              <Route path="/verifications" element={<MyVerifications />} />
              <Route path="/verifications/:id" element={<VerificationDetail />} />
            </Route>
            {/* One list for three audiences: an institution answering, a
                verifier waiting, an admin reading. The API scopes the rows. */}
            <Route path="/requests" element={<Requests />} />
            <Route path="/requests/:id" element={<RequestDetail />} />
            <Route element={<ProtectedRoute roles={['admin']} />}>
              <Route path="/admin/audit" element={<AuditLog />} />
              <Route path="/admin/institutions" element={<Institutions />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
