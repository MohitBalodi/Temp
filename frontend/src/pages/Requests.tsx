import { useState } from 'react';
import { Link } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useMe } from '@/hooks/useAuth';
import { DECISION_LABEL, STATUS_LABEL, useReviews } from '@/hooks/useReviews';

const PAGE_SIZE = 20;

const FILTERS = [
  { value: 'open', label: 'Open' },
  { value: 'pending', label: 'Waiting' },
  { value: 'needs_info', label: 'Needs info' },
  { value: 'closed', label: 'Answered' },
  { value: '', label: 'All' },
] as const;

const STATUS_STYLE: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-900',
  needs_info: 'bg-sky-100 text-sky-900',
  closed: 'bg-muted text-muted-foreground',
};

/**
 * One page for three audiences, because it is one list.
 *
 * The rows are the same facts whoever is reading; what differs is the scope
 * (the server decides that) and the wording of the heading. An institution is
 * looking at work to do, a verifier at answers they are waiting for, an admin
 * at everything.
 */
export default function Requests() {
  const { data: user } = useMe();
  const [status, setStatus] = useState<string>('open');
  const [page, setPage] = useState(1);
  const { data, isPending, isError, error } = useReviews({ page, size: PAGE_SIZE, status: status || undefined });

  const isInstitution = user?.role === 'institution';
  const heading = isInstitution
    ? 'Verification requests'
    : user?.role === 'admin'
      ? 'All verification requests'
      : 'My requests';
  const blurb = isInstitution
    ? 'Verifiers asking you to confirm a certificate. Open one to see the document and answer.'
    : user?.role === 'admin'
      ? 'Every request on the platform, read-only.'
      : 'Confirmations you asked institutions for, and what they answered.';

  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{heading}</h1>
        <p className="text-sm text-muted-foreground">{blurb}</p>
      </div>

      <div className="flex flex-wrap gap-1">
        {FILTERS.map((filter) => (
          <Button
            key={filter.label}
            variant={status === filter.value ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => {
              setStatus(filter.value);
              setPage(1);
            }}
          >
            {filter.label}
          </Button>
        ))}
      </div>

      {isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
      {isError && <p className="text-sm text-destructive">{apiErrorMessage(error)}</p>}

      {data && data.items.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            {isInstitution
              ? 'No requests. Verifiers will appear here when they ask you to confirm a certificate.'
              : 'No requests yet. You can ask an institution from any result that needs review.'}
          </CardContent>
        </Card>
      )}

      {data && data.items.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Certificate</th>
                  <th className="px-4 py-3 font-medium">
                    {isInstitution ? 'Asked by' : 'Institution'}
                  </th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Last update</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3">
                      <span className="font-mono">{item.cert_number ?? '—'}</span>
                      <span className="block text-xs text-muted-foreground">
                        read as {item.result.replace('_', ' ').toLowerCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {isInstitution ? item.requester.email : `${item.institution.code}`}
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={STATUS_STYLE[item.status] ?? ''} variant="secondary">
                        {item.decision
                          ? (DECISION_LABEL[item.decision] ?? item.decision)
                          : (STATUS_LABEL[item.status] ?? item.status)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(item.updated_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button variant="outline" size="sm" asChild>
                        <Link to={`/requests/${item.id}`}>
                          {isInstitution && item.status !== 'closed' ? 'Answer' : 'Open'}
                        </Link>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Page {page} of {pages} · {total} request{total === 1 ? '' : 's'}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
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
      )}
    </div>
  );
}
