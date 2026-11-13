import { useMutation } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { components } from '@/api/schema';

export type Verification = components['schemas']['VerificationOut'];
export type VerificationCheck = components['schemas']['CheckOut'];

export function useVerifyById() {
  return useMutation({
    mutationFn: async (certNumber: string) =>
      (await api.post<Verification>('/verify/id', { cert_number: certNumber })).data,
  });
}

export function useVerifyByQr() {
  return useMutation({
    mutationFn: async (payload: string) =>
      (await api.post<Verification>('/verify/qr', { payload })).data,
  });
}
