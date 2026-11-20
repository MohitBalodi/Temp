import { AlertTriangle, Eye } from 'lucide-react';

import type { Verification, VerificationCheck } from '@/hooks/useVerify';

/** Labels for the compared fields, as the certificate prints them. */
const FIELD_LABELS: Record<string, string> = {
  cert_number: 'Certificate number',
  student_name: 'Student name',
  roll_number: 'Roll number',
  programme: 'Programme',
  year_of_passing: 'Year of passing',
  cgpa: 'CGPA',
  marks: 'Marks',
  issue_date: 'Date of issue',
};

const PREFIX = 'field_match.';

interface Compared {
  field: string;
  label: string;
  state: string;
  onDocument: string | null;
  inRegistry: string | null;
}

function label(name: string): string {
  const field = name.slice(PREFIX.length);
  return FIELD_LABELS[field] ?? field;
}

/** The registry's value for a field, in the form the comparison used. */
function registryValue(verification: Verification, field: string): string | null {
  const cert = verification.certificate;
  if (!cert) return null;
  const values: Record<string, string | null | undefined> = {
    cert_number: cert.cert_number,
    student_name: cert.student_name,
    roll_number: cert.roll_number,
    programme: cert.programme,
    year_of_passing: String(cert.year_of_passing),
    cgpa: cert.cgpa,
    marks: cert.marks,
    issue_date: cert.issue_date,
  };
  return values[field] ?? null;
}

/** What the document said, in its own casing where we kept it. */
function documentValue(verification: Verification, field: string): string | null {
  const extracted = verification.extracted_fields as
    | { fields?: Record<string, { value?: string | null; raw?: string | null }> }
    | null
    | undefined;
  const found = extracted?.fields?.[field];
  return found?.raw || found?.value || null;
}

function compare(verification: Verification): Compared[] {
  return verification.checks
    .filter((c: VerificationCheck) => c.name.startsWith(PREFIX) && c.state)
    .map((c: VerificationCheck) => {
      const field = c.name.slice(PREFIX.length);
      return {
        field,
        label: label(c.name),
        state: c.state as string,
        onDocument: documentValue(verification, field),
        inRegistry: registryValue(verification, field),
      };
    });
}

/**
 * How the document compares with the registry, field by field.
 *
 * Three things a verifier needs before anything else: what disagrees, what
 * could not be read, and the count. Deliberately no overall percentage — a
 * document is not 80% genuine, and a single differing CGPA matters more than
 * six fields that happen to match.
 */
export default function DocumentMatch({ verification }: { verification: Verification }) {
  if (verification.method !== 'upload') return null;

  const fields = compare(verification);
  if (fields.length === 0) return null;

  const differing = fields.filter((f) => f.state === 'differs');
  const matching = fields.filter((f) => f.state === 'matches');
  const unread = fields.filter((f) => f.state === 'not_read');

  return (
    <div className="space-y-4">
      {differing.length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-amber-950">
          <p className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
            {differing.length === 1
              ? 'One printed value differs from the registry'
              : `${differing.length} printed values differ from the registry`}
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {differing.map((f) => (
              <li key={f.field} className="print-keep">
                <span className="font-medium">{f.label}</span> — document shows{' '}
                <span className="font-mono">{f.onDocument ?? '—'}</span>, institution issued{' '}
                <span className="font-mono">{f.inRegistry ?? '—'}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {unread.length > 0 && (
        <div className="rounded-lg border bg-muted/50 p-4">
          <p className="flex items-center gap-2 text-sm font-medium">
            <Eye className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
            Couldn’t read on the document: {unread.map((f) => f.label).join(', ')} — compare with
            the issued details below.
          </p>
        </div>
      )}

      <p className="text-sm text-muted-foreground">
        Document match: {matching.length} of {fields.length} fields match · {differing.length}{' '}
        differ · {unread.length} not read
      </p>
    </div>
  );
}
