import { useState } from 'react';

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
import type { Certificate } from '@/hooks/useCertificates';
import { useRevokeCertificate } from '@/hooks/useCertificates';
import { useToast } from '@/hooks/use-toast';

interface Props {
  certificate: Certificate | null;
  onClose: () => void;
}

export default function RevokeCertificateDialog({ certificate, onClose }: Props) {
  const [reason, setReason] = useState('');
  const revoke = useRevokeCertificate();
  const { toast } = useToast();

  const close = () => {
    setReason('');
    revoke.reset();
    onClose();
  };

  const submit = () => {
    if (!certificate || reason.trim().length < 3) return;
    revoke.mutate(
      { id: certificate.id, reason: reason.trim() },
      {
        onSuccess: () => {
          toast({
            title: 'Certificate revoked',
            description: `${certificate.cert_number} now verifies as REVOKED.`,
          });
          close();
        },
      },
    );
  };

  return (
    <Dialog open={Boolean(certificate)} onOpenChange={(next) => !next && close()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Revoke {certificate?.cert_number}?</DialogTitle>
          <DialogDescription>
            {certificate?.student_name} · {certificate?.programme}. Anyone verifying this
            certificate will see REVOKED. The record, its signature and its PDF stay as issued, and
            the reason goes to the audit log.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5 py-2">
          <Label htmlFor="revoke-reason">Reason</Label>
          <textarea
            id="revoke-reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Issued in error — duplicate record"
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
          {revoke.isError && (
            <p className="text-sm text-destructive">{apiErrorMessage(revoke.error)}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={close}>
            Cancel
          </Button>
          <Button
            variant="outline"
            className="border-destructive text-destructive"
            disabled={revoke.isPending || reason.trim().length < 3}
            onClick={submit}
          >
            {revoke.isPending ? 'Revoking…' : 'Revoke'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
