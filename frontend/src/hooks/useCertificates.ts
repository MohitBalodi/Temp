import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { components } from '@/api/schema';
import { saveBlob } from '@/lib/download';

export type Certificate = components['schemas']['CertificateOut'];
export type CertificateCreate = components['schemas']['CertificateCreate'];
export type CertificatePage = components['schemas']['Page_CertificateOut_'];
export type ImportResult = components['schemas']['ImportResult'];
export type ImportRowError = components['schemas']['ImportRowError'];
export type ImportErrorResponse = components['schemas']['ImportErrorResponse'];

const KEY = ['certificates'] as const;

export interface CertificateListParams {
  q: string;
  page: number;
  size: number;
}

export function useCertificates(params: CertificateListParams) {
  return useQuery({
    queryKey: [...KEY, 'list', params],
    queryFn: async () =>
      (
        await api.get<CertificatePage>('/certificates', {
          params: { q: params.q || undefined, page: params.page, size: params.size },
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}

export function useCreateCertificate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: CertificateCreate) =>
      (await api.post<Certificate>('/certificates', body)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}

export function useImportCertificates() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return (await api.post<ImportResult>('/certificates/import', form)).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}

/** Download the PDF that was issued with the certificate (served as stored,
 * never regenerated, so its SHA-256 still matches `file_sha256`). */
export function useDownloadCertificatePdf() {
  return useMutation({
    mutationFn: async (cert: Pick<Certificate, 'id' | 'cert_number'>) => {
      const { data } = await api.get<Blob>(`/certificates/${cert.id}/pdf`, {
        responseType: 'blob',
      });
      saveBlob(data, `${cert.cert_number}.pdf`);
    },
  });
}
