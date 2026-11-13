import { Search } from 'lucide-react';
import { useState } from 'react';

import { apiErrorMessage } from '@/api/client';
import QrScanner from '@/components/QrScanner';
import VerificationResult from '@/components/VerificationResult';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { Verification } from '@/hooks/useVerify';
import { useVerifyById, useVerifyByQr } from '@/hooks/useVerify';

export default function Verify() {
  const [certNumber, setCertNumber] = useState('');
  const [result, setResult] = useState<Verification | null>(null);

  const byId = useVerifyById();
  const byQr = useVerifyByQr();
  const pending = byId.isPending || byQr.isPending;
  const error = byId.error ?? byQr.error;

  const clear = () => {
    setResult(null);
    byId.reset();
    byQr.reset();
  };

  const verifyNumber = () => {
    if (!certNumber.trim()) return;
    byQr.reset();
    byId.mutate(certNumber.trim(), { onSuccess: setResult });
  };

  const verifyPayload = (payload: string) => {
    byId.reset();
    byQr.mutate(payload, { onSuccess: setResult });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Verify a certificate</h1>
        <p className="text-sm text-muted-foreground">
          Enter the certificate number or scan the QR code printed on the document. Every check
          behind the result is shown.
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Tabs defaultValue="number" onValueChange={clear}>
            <TabsList>
              <TabsTrigger value="number">Certificate number</TabsTrigger>
              <TabsTrigger value="qr">Scan QR</TabsTrigger>
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
          </Tabs>

          {error && <p className="mt-3 text-sm text-destructive">{apiErrorMessage(error)}</p>}
        </CardContent>
      </Card>

      {result ? (
        <VerificationResult verification={result} />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-muted-foreground">No result yet</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            A result appears here with its evidence: registry lookup, revocation, and the
            signatures on the record and the QR code.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
