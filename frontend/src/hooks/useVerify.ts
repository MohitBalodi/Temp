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

export type UploadAccepted = components['schemas']['UploadAccepted'];
export type JobStatus = components['schemas']['JobStatusOut'];

/** Accepted upload types, kept in step with `services/uploads.py`. */
export const UPLOAD_ACCEPT = 'application/pdf,image/png,image/jpeg';
export const UPLOAD_MAX_BYTES = 10 * 1024 * 1024;

export function useVerifyByUpload() {
  return useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append('file', file);
      // Let the browser set the multipart boundary.
      return (await api.post<UploadAccepted>('/verify/upload', body)).data;
    },
  });
}

/**
 * Poll an upload job until it finishes.
 *
 * Polling rather than a socket: the job is seconds long and the API is plain
 * HTTP. `refetchInterval` returns false once the job is settled, which stops
 * the polling instead of leaving a timer running on the result page.
 */
export function useUploadJob(jobId: string | undefined, intervalMs = 1000) {
  return useQuery({
    queryKey: [...KEY, 'job', jobId],
    queryFn: async () => (await api.get<JobStatus>(`/verify/jobs/${jobId}`)).data,
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'done' || status === 'failed' ? false : intervalMs;
    },
    // A job's state is inherently stale the moment it is read.
    staleTime: 0,
    gcTime: 0,
  });
}
