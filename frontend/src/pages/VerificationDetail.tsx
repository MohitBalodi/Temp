import { ArrowLeft } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import VerificationResult from '@/components/VerificationResult';
import { Button } from '@/components/ui/button';
import { useVerification } from '@/hooks/useVerify';

export default function VerificationDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isPending, isError, error } = useVerification(id);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Verification result</h1>
          <p className="text-sm text-muted-foreground">
            Every check behind this result, as it was recorded.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link to="/verify">
              <ArrowLeft />
              Verify another
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/verifications">History</Link>
          </Button>
        </div>
      </div>

      {isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
      {isError && (
        <p className="text-sm text-destructive">
          {apiErrorMessage(error, 'This verification could not be loaded.')}
        </p>
      )}
      {data && <VerificationResult verification={data} full />}
    </div>
  );
}
