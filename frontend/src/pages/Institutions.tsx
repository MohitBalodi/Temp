import { Check, Copy, Plus, Power, Trash2 } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { apiErrorMessage, apiFieldErrors } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import type { Institution, InstitutionCreated } from '@/hooks/useInstitutions';
import {
  useCreateInstitution,
  useDeleteInstitution,
  useInstitutions,
  useUpdateInstitution,
} from '@/hooks/useInstitutions';

const PAGE_SIZE = 20;
const EMPTY = { name: '', code: '', admin_email: '' };

export default function Institutions() {
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [created, setCreated] = useState<InstitutionCreated | null>(null);
  const [copied, setCopied] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Institution | null>(null);

  const list = useInstitutions({ page, size: PAGE_SIZE });
  const create = useCreateInstitution();
  const update = useUpdateInstitution();
  const remove = useDeleteInstitution();
  const { toast } = useToast();

  const fieldErrors = create.isError ? apiFieldErrors(create.error) : {};
  const formError = create.isError ? (fieldErrors._form ?? apiErrorMessage(create.error)) : null;

  const openCreate = (next: boolean) => {
    setCreateOpen(next);
    if (!next) {
      setForm(EMPTY);
      create.reset();
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(form, {
      onSuccess: (data) => {
        openCreate(false);
        setCopied(false);
        setCreated(data);
      },
    });
  };

  const toggleActive = (institution: Institution) =>
    update.mutate(
      { id: institution.id, is_active: !institution.is_active },
      {
        onSuccess: (updated) =>
          toast({
            title: updated.is_active ? 'Institution activated' : 'Institution deactivated',
            description: updated.is_active
              ? `${updated.code} can sign in and issue again.`
              : `${updated.code} keeps its certificates verifiable, but its users cannot sign in.`,
          }),
        onError: (error) =>
          toast({ title: 'Could not update', description: apiErrorMessage(error), variant: 'destructive' }),
      },
    );

  const doDelete = (institution: Institution) =>
    remove.mutate(institution.id, {
      onSuccess: () => {
        setConfirmDelete(null);
        toast({ title: 'Institution removed', description: `${institution.code} is gone.` });
      },
      onError: (error) => {
        setConfirmDelete(null);
        toast({
          title: 'Not removed',
          description: apiErrorMessage(error),
          variant: 'destructive',
        });
      },
    });

  const total = list.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Institutions</h1>
          <p className="text-sm text-muted-foreground">
            Each institution gets an Ed25519 keypair; the private key stays on the server.
          </p>
        </div>
        <Button onClick={() => openCreate(true)}>
          <Plus />
          Add institution
        </Button>
      </div>

      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead className="text-right">Certificates</TableHead>
              <TableHead className="text-right">Users</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.isPending && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {list.isError && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-destructive">
                  {apiErrorMessage(list.error)}
                </TableCell>
              </TableRow>
            )}
            {list.data?.items.map((institution) => (
              <TableRow key={institution.id}>
                <TableCell className="font-mono text-xs">{institution.code}</TableCell>
                <TableCell className="font-medium">
                  <input
                    className="w-full bg-transparent outline-none focus:underline"
                    defaultValue={institution.name}
                    aria-label={`Name of ${institution.code}`}
                    onBlur={(e) => {
                      const name = e.target.value.trim();
                      if (name && name !== institution.name) update.mutate({ id: institution.id, name });
                    }}
                  />
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {institution.certificate_count}
                </TableCell>
                <TableCell className="text-right tabular-nums">{institution.user_count}</TableCell>
                <TableCell>
                  <Badge variant={institution.is_active ? 'secondary' : 'destructive'}>
                    {institution.is_active ? 'active' : 'inactive'}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleActive(institution)}
                    title={institution.is_active ? 'Deactivate' : 'Activate'}
                    aria-label={`${institution.is_active ? 'Deactivate' : 'Activate'} ${institution.code}`}
                  >
                    <Power />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmDelete(institution)}
                    title="Delete (only if it never issued anything)"
                    aria-label={`Delete ${institution.code}`}
                  >
                    <Trash2 />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total} institution{total === 1 ? '' : 's'}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="tabular-nums">
            Page {page} of {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>

      {/* Create */}
      <Dialog open={createOpen} onOpenChange={openCreate}>
        <DialogContent>
          <form onSubmit={submit}>
            <DialogHeader>
              <DialogTitle>Add institution</DialogTitle>
              <DialogDescription>
                A keypair is generated and the first user’s password is shown once.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {(
                [
                  { name: 'name', label: 'Name', placeholder: 'Riverdale Institute of Science' },
                  { name: 'code', label: 'Code', placeholder: 'RVS' },
                  { name: 'admin_email', label: 'First user email', placeholder: 'registrar@rvs.test' },
                ] as const
              ).map((field) => (
                <div key={field.name} className="space-y-1.5">
                  <Label htmlFor={field.name}>{field.label}</Label>
                  <Input
                    id={field.name}
                    value={form[field.name]}
                    placeholder={field.placeholder}
                    onChange={(e) => setForm({ ...form, [field.name]: e.target.value })}
                  />
                  {fieldErrors[field.name] && (
                    <p className="text-sm text-destructive">{fieldErrors[field.name]}</p>
                  )}
                </div>
              ))}
              {formError && <p className="text-sm text-destructive">{formError}</p>}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => openCreate(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? 'Creating…' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* The password, once */}
      <Dialog open={Boolean(created)} onOpenChange={() => setCreated(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{created?.institution.code} created</DialogTitle>
            <DialogDescription>
              Copy this password now — it is stored only as a hash and cannot be shown again.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">First user</p>
              <p className="font-medium">{created?.user.email}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Password</p>
              <div className="mt-1 flex items-center gap-2">
                <code className="flex-1 rounded-md bg-muted px-3 py-2 font-mono text-sm">
                  {created?.password}
                </code>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    if (!created) return;
                    await navigator.clipboard.writeText(created.password);
                    setCopied(true);
                  }}
                >
                  {copied ? <Check /> : <Copy />}
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setCreated(null)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={Boolean(confirmDelete)} onOpenChange={() => setConfirmDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {confirmDelete?.code}?</DialogTitle>
            <DialogDescription>
              {confirmDelete?.certificate_count
                ? `${confirmDelete.code} has ${confirmDelete.certificate_count} certificate(s), so it cannot be deleted. Deactivate it instead to keep them verifiable.`
                : 'This removes the institution and its users. Issued certificates would block it.'}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="outline"
              className="border-destructive text-destructive"
              disabled={remove.isPending || Boolean(confirmDelete?.certificate_count)}
              onClick={() => confirmDelete && doDelete(confirmDelete)}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
