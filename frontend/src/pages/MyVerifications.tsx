import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useMe } from '@/hooks/useAuth';
import { useMyVerifications } from '@/hooks/useVerify';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 20;

const RESULT_STYLES: Record<string, string> = {
  VERIFIED: 'bg-emerald-600 text-white hover:bg-emerald-600',
  MISMATCH: 'bg-red-600 text-white hover:bg-red-600',
  MANUAL_REVIEW: 'bg-amber-500 text-white hover:bg-amber-500',
  REVOKED: 'bg-zinc-600 text-white hover:bg-zinc-600',
};

const METHOD_LABELS: Record<string, string> = {
  id: 'Number',
  qr: 'QR',
  upload: 'Upload',
};

export default function MyVerifications() {
  const { data: user } = useMe();
  const [page, setPage] = useState(1);
  const list = useMyVerifications({ page, size: PAGE_SIZE });

  const total = list.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {user?.role === 'admin' ? 'All verifications' : 'My verifications'}
        </h1>
        <p className="text-sm text-muted-foreground">Newest first. Open one to see its checks.</p>
      </div>

      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Certificate no.</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>Method</TableHead>
              <TableHead>Checked at</TableHead>
              <TableHead className="text-right">Details</TableHead>
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
                  Nothing verified yet.
                </TableCell>
              </TableRow>
            )}
            {list.data?.items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-mono text-xs">{item.cert_number ?? '—'}</TableCell>
                <TableCell>
                  <Badge className={cn(RESULT_STYLES[item.result])}>{item.result}</Badge>
                </TableCell>
                <TableCell>{METHOD_LABELS[item.method] ?? item.method}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {new Date(item.created_at).toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm" asChild>
                    <Link to={`/verifications/${item.id}`}>Open</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total} verification{total === 1 ? '' : 's'}
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
