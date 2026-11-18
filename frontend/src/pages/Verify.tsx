import { Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import QrScanner from '@/components/QrScanner';
import UploadDropzone from '@/components/UploadDropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useUploadJob, useVerifyById, useVerifyByQr, useVerifyByUpload } from '@/hooks/useVerify';

/** What the spinner says at each stage of an upload job. */
const JOB_LABELS: Record<string, string> = {
  queued: 'Queued for extraction…',
  running: 'Reading the document…',
  done: 'Done',
  failed: 'Extraction failed',
};

export default function Verify() {
  const navigate = useNavigate();
  const [certNumber, setCertNumber] = useState('');

  const byId = useVerifyById();
  const byQr = useVerifyByQr();
  const byUpload = useVerifyByUpload();

  // Set once an upload is accepted; the job is then polled until it settles.
  const [jobId, setJobId] = useState<string>();
  const [fileName, setFileName] = useState<string>();
  const job = useUploadJob(jobId);

  const uploadBusy = byUpload.isPending || (Boolean(jobId) && job.data?.status !== 'failed' && !job.data?.verification_id);
  const pending = byId.isPending || byQr.isPending;
  const error = byId.error ?? byQr.error ?? byUpload.error ?? job.error;

  // The result lives at its own URL, so it can be shared, reopened and printed.
  const showResult = (verification: { id: string }) => navigate(`/verifications/${verification.id}`);

  const clear = () => {
    byId.reset();
    byQr.reset();
    byUpload.reset();
    setJobId(undefined);
    setFileName(undefined);
  };

  const verifyNumber = () => {
    if (!certNumber.trim()) return;
    byQr.reset();
    byId.mutate(certNumber.trim(), { onSuccess: showResult });
  };

  const verifyPayload = (payload: string) => {
    byId.reset();
    byQr.mutate(payload, { onSuccess: showResult });
  };

  const verifyFile = (file: File) => {
    byId.reset();
    byQr.reset();
    setFileName(file.name);
    byUpload.mutate(file, { onSuccess: (accepted) => setJobId(accepted.job_id) });
  };

  // The job finishes in the worker, so the redirect happens when the poll
  // reports it rather than in a mutation callback.
  const finishedId = job.data?.verification_id;
  useEffect(() => {
    if (finishedId) navigate(`/verifications/${finishedId}`);
  }, [finishedId, navigate]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Verify a certificate</h1>
        <p className="text-sm text-muted-foreground">
          Enter the certificate number, scan the QR code printed on the document, or upload the
          document itself. Every check behind the result is shown.
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Tabs defaultValue="number" onValueChange={clear}>
            <TabsList>
              <TabsTrigger value="number">Certificate number</TabsTrigger>
              <TabsTrigger value="qr">Scan QR</TabsTrigger>
              <TabsTrigger value="upload">Upload document</TabsTrigger>
            </TabsList>

            <TabsContent value="number" className="mt-4">
              <form
                className="flex flex-wrap items-end gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  verifyNumber();
                }}
              >
                <div className="min-w-64 flex-1 space-y-1.5">
                  <Label htmlFor="cert-number">Certificate number</Label>
                  <Input
                    id="cert-number"
                    value={certNumber}
                    onChange={(e) => setCertNumber(e.target.value)}
                    placeholder="NBIT2024CS0001"
                    autoComplete="off"
                    spellCheck={false}
                  />
                </div>
                <Button type="submit" disabled={pending || !certNumber.trim()}>
                  <Search />
                  {pending ? 'Checking…' : 'Verify'}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="qr" className="mt-4">
              <QrScanner onDecoded={verifyPayload} disabled={pending} />
            </TabsContent>

            <TabsContent value="upload" className="mt-4">
              <UploadDropzone
                onFile={verifyFile}
                disabled={pending}
                busy={uploadBusy}
                busyLabel={
                  byUpload.isPending
                    ? 'Uploading…'
                    : (JOB_LABELS[job.data?.status ?? 'queued'] ?? 'Working…')
                }
                submittedName={fileName}
              />
              {job.data?.status === 'failed' && (
                <p className="mt-3 text-sm text-destructive" role="alert">
                  {job.data.error ?? 'The document could not be read.'} Nothing was decided about
                  the document — try a clearer scan, or verify by certificate number instead.
                </p>
              )}
            </TabsContent>
          </Tabs>

          {error && <p className="mt-3 text-sm text-destructive">{apiErrorMessage(error)}</p>}
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">
        The result opens on its own page, with every check and a printable copy.
      </p>
    </div>
  );
}
