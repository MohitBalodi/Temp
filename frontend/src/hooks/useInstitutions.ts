import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { components } from '@/api/schema';

export type Institution = components['schemas']['InstitutionOut'];
export type InstitutionCreate = components['schemas']['InstitutionCreate'];
export type InstitutionCreated = components['schemas']['InstitutionCreated'];
export type InstitutionUpdate = components['schemas']['InstitutionUpdate'];
export type InstitutionPage = components['schemas']['Page_InstitutionOut_'];

const KEY = ['institutions'] as const;

export function useInstitutions(params: { page: number; size: number }) {
  return useQuery({
    queryKey: [...KEY, 'list', params],
    queryFn: async () => (await api.get<InstitutionPage>('/institutions', { params })).data,
    placeholderData: keepPreviousData,
  });
}

export function useCreateInstitution() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: InstitutionCreate) =>
      (await api.post<InstitutionCreated>('/institutions', body)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateInstitution() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: InstitutionUpdate & { id: number }) =>
      (await api.patch<Institution>(`/institutions/${id}`, body)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteInstitution() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/institutions/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
}
