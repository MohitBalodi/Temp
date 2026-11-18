import { Building2, MessageSquare, Send } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useMe } from '@/hooks/useAuth';
import { DECISION_LABEL, STATUS_LABEL } from '@/hooks/useReviews';
import type { Verification } from '@/hooks/useVerify';

/** Results the system could not settle — the only ones worth escalating. */
const ESCALATABLE = new Set(['MANUAL_REVIEW', 'MISMATCH']);

function when(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleDateString() : '';
}

/**
 * What the issuing institution said, and the button to ask them.
 *
 * Shown on the result page below the checks. The institution's answer is
 * presented as a separate, later fact — it is never folded into the result,
 * which records what the system itself concluded.
 */
export default function VerificationRequests({
  verification,
  onRequest,
}: {
  verification: Verification;
  onRequest: () => void;
}) {
  const { data: user } = useMe();
  const requests = verification.reviews ?? [];
  const open = requests.find((r) => r.status !== 'closed');
  const canAsk =
    user?.role === 'verifier' && ESCALATABLE.has(verification.result) && !open && !requests.length;

  if (!requests.length && !canAsk) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">The issuing institution</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {requests.map((request) => (
          <div key={request.id} className="print-keep space-y-1 text-sm">
            {request.decision ? (
              <p className="font-medium">
                {request.decision === 'not_issued' ? (
                  <>
                    {request.institution_name} states it did not issue this certificate
                    {request.decided_at && ` (${when(request.decided_at)})`}.
                  </>
                ) : (
                  <>
                    {DECISION_LABEL[request.decision] ?? request.decision} by{' '}
                    {request.institution_code}
                    {request.decided_at && ` on ${when(request.decided_at)}`}.
                  </>
                )}
              </p>
            ) : (
              <p className="font-medium">
                {STATUS_LABEL[request.status] ?? request.status} — {request.institution_code}, asked{' '}
                {when(request.created_at)}.
              </p>
            )}
            {request.decision_note && (
              <p className="text-muted-foreground">“{request.decision_note}”</p>
            )}
            <Button variant="link" className="h-auto p-0 text-sm" asChild>
              <Link to={`/requests/${request.id}`}>
                <MessageSquare />
                Open the request
              </Link>
            </Button>
          </div>
        ))}

        {canAsk && (
          <div className="space-y-2 print:hidden">
            <p className="text-sm text-muted-foreground">
              This result is not a verdict on the document — only the institution that issued it can
              settle it. Ask them, and their answer will appear here.
            </p>
            <Button onClick={onRequest}>
              <Send />
              Request confirmation from issuing institution
            </Button>
          </div>
        )}

        {!canAsk && !requests.length && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Building2 className="h-4 w-4" aria-hidden />
            No request has been sent about this result.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
