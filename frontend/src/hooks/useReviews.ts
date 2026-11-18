import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { api } from '@/api/client';
import type { components } from '@/api/schema';

export type ReviewCase = components['schemas']['ReviewOut'];
export type ReviewListItem = components['schemas']['ReviewListItem'];
export type ReviewPage = components['schemas']['Page_ReviewListItem_'];
export type ReviewCounts = components['schemas']['ReviewCounts'];
export type ReviewMessage = components['schemas']['MessageOut'];
export type InstitutionOption = components['schemas']['InstitutionOption'];
export type CertificateFields = components['schemas']['CertificateFields'];

const KEY = ['reviews'] as const;

/** Wording for each status and decision, in the verifier's terms. */
export const STATUS_LABEL: Record<string, string> = {
  pending: 'Waiting for the institution',
  needs_info: 'The institution asked a question',
  closed: 'Answered',
};

export const DECISION_LABEL: Record<string, string> = {
  confirmed: 'Confirmed genuine',
  confirmed_added: 'Confirmed and added to the registry',
  not_issued: 'The institution has no such record',
};

export function useReviews(params: { page: number; size: number; status?: string }) {
  return useQuery({
    queryKey: [...KEY, 'list', params],
    queryFn: async () => (await api.get<ReviewPage>('/reviews', { params })).data,
    placeholderData: keepPreviousData,
  });
}

export function useReview(id: string | undefined) {
  return useQuery({
    queryKey: [...KEY, 'detail', id],
    queryFn: async () => (await api.get<ReviewCase>(`/reviews/${id}`)).data,
    enabled: Boolean(id),
  });
}

/**
 * Open-request count for the nav badge.
 *
 * Scoped server-side, so the same hook serves an institution (requests to
 * answer) and a verifier (requests they are waiting on).
 */
export function useReviewCounts(enabled = true) {
  return useQuery({
    queryKey: [...KEY, 'counts'],
    queryFn: async () => (await api.get<ReviewCounts>('/reviews/counts')).data,
    enabled,
    staleTime: 30_000,
  });
}

export function useInstitutionOptions(enabled = true) {
  return useQuery({
    queryKey: ['institutions', 'options'],
    queryFn: async () => (await api.get<InstitutionOption[]>('/institutions/options')).data,
    enabled,
    staleTime: 5 * 60_000,
  });
}

/** Invalidate everything a change to one case can affect. */
function useRefresh() {
  const queryClient = useQueryClient();
  return (id?: string) => {
    void queryClient.invalidateQueries({ queryKey: KEY });
    void queryClient.invalidateQueries({ queryKey: ['verifications'] });
    if (id) void queryClient.invalidateQueries({ queryKey: [...KEY, 'detail', id] });
  };
}

export function useCreateReview() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: {
      verification_id: string;
      institution_id?: number | null;
      note?: string | null;
    }) => (await api.post<ReviewCase>('/reviews', body)).data,
    onSuccess: (data) => refresh(data.id),
  });
}

export function usePostMessage(caseId: string) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: string) =>
      (await api.post<ReviewMessage>(`/reviews/${caseId}/messages`, { body })).data,
    onSuccess: () => refresh(caseId),
  });
}

export function useAskForInfo(caseId: string) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: string) =>
      (await api.post<ReviewCase>(`/reviews/${caseId}/needs-info`, { body })).data,
    onSuccess: () => refresh(caseId),
  });
}

/** The three answers an institution can give, as one call. */
export type Decision =
  | { decision: 'confirmed'; note?: string | null }
  | { decision: 'confirmed_added'; certificate: CertificateFields }
  | { decision: 'not_issued'; reason: string };

export function useDecide(caseId: string) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: Decision) =>
      (await api.post<ReviewCase>(`/reviews/${caseId}/decision`, body)).data,
    onSuccess: () => refresh(caseId),
  });
}

/**
 * The uploaded document as a blob URL, for an <img> or <iframe> preview.
 *
 * Fetched through axios rather than pointed at by `src`: the endpoint needs
 * the bearer token, and a browser sends no Authorization header for an image
 * or a frame. The object URL is revoked when the query is discarded, so a
 * long-lived tab does not accumulate copies of the file.
 */
export function useReviewDocument(caseId: string | undefined, enabled = true) {
  const query = useQuery({
    queryKey: [...KEY, 'document', caseId],
    queryFn: async () => {
      const { data, headers } = await api.get<Blob>(`/reviews/${caseId}/document`, {
        responseType: 'blob',
      });
      return {
        url: URL.createObjectURL(data),
        mime: String(headers['content-type'] ?? data.type ?? ''),
      };
    },
    enabled: Boolean(caseId) && enabled,
    staleTime: Infinity,
    gcTime: 5 * 60_000,
  });

  useEffect(() => {
    const url = query.data?.url;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [query.data?.url]);

  return query;
}
