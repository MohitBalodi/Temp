import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { components } from '@/api/schema';

export type Verification = components['schemas']['VerificationOut'];
export type VerificationCheck = components['schemas']['CheckOut'];
export type VerificationListItem = components['schemas']['VerificationListItem'];
export type VerificationPage = components['schemas']['Page_VerificationListItem_'];

const KEY = ['verifications'] as const;

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

export function useVerification(id: string | undefined) {
  return useQuery({
    queryKey: [...KEY, 'detail', id],
    queryFn: async () => (await api.get<Verification>(`/verifications/${id}`)).data,
    enabled: Boolean(id),
  });
}

export function useMyVerifications(params: { page: number; size: number }) {
  return useQuery({
    queryKey: [...KEY, 'list', params],
    queryFn: async () => (await api.get<VerificationPage>('/verifications', { params })).data,
    placeholderData: keepPreviousData,
  });
}
