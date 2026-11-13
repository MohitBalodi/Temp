import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';

import { SESSION_EXPIRED_EVENT } from '@/api/client';
import AppLayout from '@/components/AppLayout';
import ProtectedRoute from '@/components/ProtectedRoute';
import { Toaster } from '@/components/ui/toaster';
import Certificates from '@/pages/Certificates';
import Dashboard from '@/pages/Dashboard';
import ImportCertificates from '@/pages/ImportCertificates';
import Login from '@/pages/Login';
import Verify from '@/pages/Verify';

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
              <Route path="/verify" element={<Verify />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
