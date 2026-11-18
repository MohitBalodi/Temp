import { Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import UploadDropzone from '@/components/UploadDropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useUploadJob, useVerifyById, useVerifyByUpload } from '@/hooks/useVerify';

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
  const byUpload = useVerifyByUpload();

  // Set once an upload is accepted; the job is then polled until it settles.
  const [jobId, setJobId] = useState<string>();
  const [fileName, setFileName] = useState<string>();
  const job = useUploadJob(jobId);

  const uploadBusy =
    byUpload.isPending ||
    (Boolean(jobId) && job.data?.status !== 'failed' && !job.data?.verification_id);
  const pending = byId.isPending;
  const error = byId.error ?? byUpload.error ?? job.error;

  // The result lives at its own URL, so it can be shared, reopened and printed.
  const showResult = (verification: { id: string }) => navigate(`/verifications/${verification.id}`);

  const clear = () => {
    byId.reset();
    byUpload.reset();
    setJobId(undefined);
    setFileName(undefined);
  };

  const verifyNumber = () => {
    if (!certNumber.trim()) return;
    byId.mutate(certNumber.trim(), { onSuccess: showResult });
  };

  const verifyFile = (file: File) => {
    byId.reset();
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
          Photograph the certificate, upload it as an image or a PDF, or enter the certificate
          number. Every check behind the result is shown.
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Tabs defaultValue="document" onValueChange={clear}>
            <TabsList>
              <TabsTrigger value="document">Verify document</TabsTrigger>
              <TabsTrigger value="number">Certificate number</TabsTrigger>
            </TabsList>

            {/* One tab for anything that *is* the document: a photo, an image
                file or a PDF. The QR code and the printed text are both read
                from whatever arrives, server-side, so the verifier no longer
                has to decide in advance which of the two to rely on. */}
            <TabsContent value="document" className="mt-4">
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
                  the document — try a clearer photo, or verify by certificate number instead.
                </p>
              )}
            </TabsContent>

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
