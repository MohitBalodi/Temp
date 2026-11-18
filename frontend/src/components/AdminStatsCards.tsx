import { Link } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAdminStats } from '@/hooks/useAdmin';
import { cn } from '@/lib/utils';

const RESULT_STYLES: Record<string, string> = {
  VERIFIED: 'text-emerald-600',
  MISMATCH: 'text-red-600',
  MANUAL_REVIEW: 'text-amber-600',
  REVOKED: 'text-zinc-600',
};

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | string;
  hint?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      {hint && <CardContent className="pt-0 text-xs text-muted-foreground">{hint}</CardContent>}
    </Card>
  );
}

export default function AdminStatsCards() {
  const { data, isPending, isError, error } = useAdminStats();

  if (isPending) return <p className="text-sm text-muted-foreground">Loading statistics…</p>;
  if (isError) return <p className="text-sm text-destructive">{apiErrorMessage(error)}</p>;

  const recent = data.last_7_days;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Institutions"
          value={data.institutions}
          hint={`${data.users} user${data.users === 1 ? '' : 's'} in total`}
        />
        <Stat
          label="Certificates"
          value={data.certificates}
          hint={`${data.certificates_revoked} revoked`}
        />
        <Stat
          label="Verifications"
          value={data.verifications}
          hint={`${recent.verifications} in the last 7 days`}
        />
        <Stat
          label="Logins (7 days)"
          value={recent.logins}
          hint={`${recent.failed_logins} failed`}
        />
      </div>

      {/* Tier 2 item 9. The failure mode worth watching is an institution
          that never answers, so the overdue count sits beside the open one. */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Verification requests</CardTitle>
          <CardDescription>
            Verifiers waiting on an institution to confirm a document.{' '}
            <Link to="/requests" className="underline">
              All requests
            </Link>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">Open</dt>
              <dd className="text-2xl font-semibold tabular-nums">{data.requests_open}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                Open more than 7 days
              </dt>
              <dd
                className={cn(
                  'text-2xl font-semibold tabular-nums',
                  data.requests_open_over_7_days > 0 && 'text-amber-600',
                )}
              >
                {data.requests_open_over_7_days}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Verification results</CardTitle>
          <CardDescription>
            Every verification ever run. <Link to="/admin/audit" className="underline">Audit log</Link>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-4">
            {Object.entries(data.verifications_by_result).map(([result, count]) => (
              <div key={result}>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                  {result.replace('_', ' ')}
                </dt>
                <dd className={cn('text-2xl font-semibold tabular-nums', RESULT_STYLES[result])}>
                  {count}
                </dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
