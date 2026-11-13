import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useState } from 'react';

import { apiErrorMessage } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
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
import { useAuditLog } from '@/hooks/useAdmin';
import { useDebounced } from '@/hooks/useDebounced';

const PAGE_SIZE = 25;

/** Prefixes worth one click. The filter matches by prefix, so "auth." covers
 * successes and failures alike. */
const QUICK_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Logins', value: 'auth.login' },
  { label: 'Failed logins', value: 'auth.login_failed' },
  { label: 'Certificates', value: 'certificate.' },
  { label: 'Verifications', value: 'verification.' },
  { label: 'Institutions', value: 'institution.' },
];

export default function AuditLog() {
  const [action, setAction] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);

  const debouncedAction = useDebounced(action.trim());
  const list = useAuditLog({
    action: debouncedAction,
    date_from: dateFrom,
    date_to: dateTo,
    page,
    size: PAGE_SIZE,
  });

  const total = list.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const reset = () => {
    setAction('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
        <p className="text-sm text-muted-foreground">
          Append-only: rows can be added but never changed or removed. Failed logins keep the email
          domain only.
        </p>
      </div>

      <Card className="space-y-4 p-4">
        <div className="flex flex-wrap gap-2">
          {QUICK_FILTERS.map((filter) => (
            <Button
              key={filter.label}
              variant={debouncedAction === filter.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setAction(filter.value);
                setPage(1);
              }}
            >
              {filter.label}
            </Button>
          ))}
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="audit-action">Action prefix</Label>
            <Input
              id="audit-action"
              className="w-56"
              value={action}
              placeholder="certificate."
              onChange={(e) => {
                setAction(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="audit-from">From</Label>
            <Input
              id="audit-from"
              type="date"
              className="w-40"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="audit-to">To</Label>
            <Input
              id="audit-to"
              type="date"
              className="w-40"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={reset}>
            <X />
            Clear
          </Button>
        </div>
      </Card>

      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-44">When</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Entity</TableHead>
              <TableHead>Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.isPending && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {list.isError && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-destructive">
                  {apiErrorMessage(list.error)}
                </TableCell>
              </TableRow>
            )}
            {list.data?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  No audit entries match these filters.
                </TableCell>
              </TableRow>
            )}
            {list.data?.items.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="text-sm text-muted-foreground">
                  {new Date(entry.created_at).toLocaleString()}
                </TableCell>
                <TableCell className="font-mono text-xs">{entry.action}</TableCell>
                <TableCell className="text-sm">{entry.actor_email ?? '—'}</TableCell>
                <TableCell className="text-sm">{entry.entity}</TableCell>
                <TableCell className="max-w-md truncate font-mono text-xs text-muted-foreground">
                  {Object.entries(entry.meta ?? {})
                    .map(([key, value]) => `${key}=${value ?? '—'}`)
                    .join('  ') || '—'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total} entr{total === 1 ? 'y' : 'ies'}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            aria-label="Previous page"
          >
            <ChevronLeft />
          </Button>
          <span className="tabular-nums">
            Page {page} of {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
            aria-label="Next page"
          >
            <ChevronRight />
          </Button>
        </div>
      </div>
    </div>
  );
}
