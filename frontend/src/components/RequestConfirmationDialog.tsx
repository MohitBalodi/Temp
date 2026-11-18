import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import type { Verification } from '@/hooks/useVerify';
import { useCreateReview, useInstitutionOptions } from '@/hooks/useReviews';

interface Props {
  verification: Verification | null;
  onClose: () => void;
}

/**
 * Ask the issuing institution to confirm a result the system could not settle.
 *
 * The institution is pre-selected when the document identified one — a known
 * certificate is always sent to its own issuer, so there is nothing to choose
 * and the field is shown as a fact. Only an unidentified document gets the
 * dropdown.
 */
export default function RequestConfirmationDialog({ verification, onClose }: Props) {
  const [note, setNote] = useState('');
  const [institutionId, setInstitutionId] = useState<string>('');
  const create = useCreateReview();
  const navigate = useNavigate();
  const { toast } = useToast();

  const known = verification?.certificate?.institution ?? null;
  const options = useInstitutionOptions(Boolean(verification) && !known);

  const close = () => {
    setNote('');
    setInstitutionId('');
    create.reset();
    onClose();
  };

  const submit = () => {
    if (!verification) return;
    if (!known && !institutionId) return;
    create.mutate(
      {
        verification_id: verification.id,
        institution_id: known ? null : Number(institutionId),
        note: note.trim() || null,
      },
      {
        onSuccess: (created) => {
          toast({
            title: 'Request sent',
            description: `${created.institution.code} has been asked to confirm this document.`,
          });
          close();
          navigate(`/requests/${created.id}`);
        },
      },
    );
  };

  return (
    <Dialog open={Boolean(verification)} onOpenChange={(next) => !next && close()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request confirmation from the issuing institution</DialogTitle>
          <DialogDescription>
            The institution sees this result, the document you uploaded and the fields that were
            read from it, and answers whether it issued this certificate. Nothing about the result
            changes in the meantime — the answer is added beside it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="request-institution">Institution</Label>
            {known ? (
              <p id="request-institution" className="text-sm">
                {known.name} ({known.code})
                <span className="block text-xs text-muted-foreground">
                  Taken from the certificate number on the document, so it cannot be sent
                  elsewhere.
                </span>
              </p>
            ) : (
              <>
                <select
                  id="request-institution"
                  value={institutionId}
                  onChange={(e) => setInstitutionId(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="">Choose an institution…</option>
                  {(options.data ?? []).map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name} ({option.code})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  The document did not identify an institution, so choose the one named on it.
                </p>
              </>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="request-note">Note (optional)</Label>
            <textarea
              id="request-note"
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="The holder presented a printed copy; the number is not in the registry."
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          {create.error && (
            <p className="text-sm text-destructive" role="alert">
              {apiErrorMessage(create.error)}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={close} disabled={create.isPending}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={create.isPending || (!known && !institutionId)}>
            {create.isPending ? 'Sending…' : 'Send request'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
