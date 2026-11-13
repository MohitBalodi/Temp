import { Ban, ChevronLeft, ChevronRight, Download, Search, Upload } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import AddCertificateDialog from '@/components/AddCertificateDialog';
import RevokeCertificateDialog from '@/components/RevokeCertificateDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useMe } from '@/hooks/useAuth';
import type { Certificate } from '@/hooks/useCertificates';
import { useCertificates, useDownloadCertificatePdf } from '@/hooks/useCertificates';
import { useDebounced } from '@/hooks/useDebounced';
import { useToast } from '@/hooks/use-toast';

const PAGE_SIZE = 20;

export default function Certificates() {
  const { data: user } = useMe();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const q = useDebounced(search.trim());
  const list = useCertificates({ q, page, size: PAGE_SIZE });
  const { toast } = useToast();
  const download = useDownloadCertificatePdf();
  const [toRevoke, setToRevoke] = useState<Certificate | null>(null);

  const isInstitution = user?.role === 'institution';
  const isAdmin = user?.role === 'admin';
  const total = list.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const columnCount = isAdmin ? 9 : 8;

  const downloadPdf = (cert: { id: string; cert_number: string }) =>
    download.mutate(cert, {
      onError: (error) =>
        toast({
          title: 'Download failed',
          description: apiErrorMessage(error, 'The issued PDF is not available.'),
          variant: 'destructive',
        }),
    });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Certificates</h1>
          <p className="text-sm text-muted-foreground">
            {isInstitution
              ? `Registry for ${user?.institution?.name ?? 'your institution'}.`
              : 'All institutions.'}
          </p>
        </div>
        {isInstitution && (
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to="/certificates/import">
                <Upload />
                Import CSV
              </Link>
            </Button>
            <AddCertificateDialog />
          </div>
        )}
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search number, roll number or name"
          aria-label="Search certificates"
          className="pl-8"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Certificate no.</TableHead>
              <TableHead>Student</TableHead>
              <TableHead>Roll no.</TableHead>
              <TableHead>Programme</TableHead>
              <TableHead className="text-right">Year</TableHead>
              <TableHead className="text-right">CGPA / Marks</TableHead>
              {isAdmin && <TableHead>Institution</TableHead>}
              <TableHead>Status</TableHead>
              <TableHead className="text-right">PDF</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.isPending && (
              <TableRow>
                <TableCell colSpan={columnCount} className="py-8 text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {list.isError && (
              <TableRow>
                <TableCell colSpan={columnCount} className="py-8 text-center text-destructive">
                  {apiErrorMessage(list.error)}
                </TableCell>
              </TableRow>
            )}
            {list.data?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={columnCount} className="py-8 text-center text-muted-foreground">
                  {q ? `No certificates match “${q}”.` : 'No certificates yet.'}
                </TableCell>
              </TableRow>
            )}
            {list.data?.items.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-mono text-xs">{c.cert_number}</TableCell>
                <TableCell className="font-medium">{c.student_name}</TableCell>
                <TableCell className="font-mono text-xs">{c.roll_number}</TableCell>
                <TableCell>{c.programme}</TableCell>
                <TableCell className="text-right tabular-nums">{c.year_of_passing}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {[c.cgpa, c.marks && `${c.marks}%`].filter(Boolean).join(' / ')}
                </TableCell>
                {isAdmin && <TableCell>{c.institution.code}</TableCell>}
                <TableCell>
                  <Badge variant={c.status === 'active' ? 'secondary' : 'destructive'}>
                    {c.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={download.isPending && download.variables?.id === c.id}
                    onClick={() => downloadPdf(c)}
                    aria-label={`Download PDF for ${c.cert_number}`}
                    title="Download the issued PDF"
                  >
                    <Download />
                  </Button>
                  {isInstitution && c.status === 'active' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setToRevoke(c)}
                      aria-label={`Revoke ${c.cert_number}`}
                      title="Revoke this certificate"
                    >
                      <Ban />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <RevokeCertificateDialog certificate={toRevoke} onClose={() => setToRevoke(null)} />

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total} certificate{total === 1 ? '' : 's'}
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
