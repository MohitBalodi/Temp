import { CheckCircle2, CircleHelp, MinusCircle, XCircle } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Verification, VerificationCheck } from '@/hooks/useVerify';
import { cn } from '@/lib/utils';

/** Wording and colour per result. Never "fake" or "forged": absence of
 * evidence is not fraud, so an unknown record reads as "needs review". */
const RESULTS: Record<string, { label: string; blurb: string; className: string }> = {
  VERIFIED: {
    label: 'Verified',
    blurb: 'The record matches the registry and the signature of the issuing institution.',
    className: 'bg-emerald-600 text-white',
  },
  MISMATCH: {
    label: 'Mismatch',
    blurb: 'The document and the registry record do not agree. See the checks below.',
    className: 'bg-red-600 text-white',
  },
  MANUAL_REVIEW: {
    label: 'Needs review',
    blurb: 'Not enough evidence to decide automatically. An institution should look at this.',
    className: 'bg-amber-500 text-white',
  },
  REVOKED: {
    label: 'Revoked',
    blurb: 'The issuing institution has revoked this certificate.',
    className: 'bg-zinc-500 text-white',
  },
};

const CHECK_ICONS = {
  pass: { Icon: CheckCircle2, className: 'text-emerald-600' },
  fail: { Icon: XCircle, className: 'text-red-600' },
  skipped: { Icon: MinusCircle, className: 'text-muted-foreground' },
  uncertain: { Icon: CircleHelp, className: 'text-amber-500' },
} as const;

const CHECK_LABELS: Record<string, string> = {
  registry_lookup: 'Registry lookup',
  revocation: 'Revocation',
  record_signature: 'Registry signature',
  qr_signature: 'QR signature',
  file_hash: 'File hash',
  field_match: 'Field match',
};

function CheckRow({ check }: { check: VerificationCheck }) {
  const { Icon, className } = CHECK_ICONS[check.status as keyof typeof CHECK_ICONS] ?? CHECK_ICONS.skipped;
  return (
    <li className="flex gap-3 py-2">
      <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', className)} aria-hidden />
      <div className="min-w-0">
        <p className="text-sm font-medium">
          {CHECK_LABELS[check.name] ?? check.name}
          <span className="sr-only">: {check.status}</span>
        </p>
        <p className="text-sm text-muted-foreground">{check.detail}</p>
      </div>
    </li>
  );
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === '') return null;
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{value}</dd>
    </div>
  );
}

export default function VerificationResult({ verification }: { verification: Verification }) {
  const result = RESULTS[verification.result] ?? {
    label: verification.result,
    blurb: '',
    className: 'bg-zinc-500 text-white',
  };
  const cert = verification.certificate;
  const grade = [cert?.cgpa && `CGPA ${cert.cgpa}`, cert?.marks && `${cert.marks}%`]
    .filter(Boolean)
    .join(' / ');

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={cn(
              'rounded-md px-3 py-1 text-sm font-semibold uppercase tracking-wide',
              result.className,
            )}
            role="status"
          >
            {result.label}
          </span>
          <CardTitle className="text-base font-mono">
            {cert?.cert_number ?? verification.extracted_fields?.cert_number ?? '—'}
          </CardTitle>
        </div>
        <p className="text-sm text-muted-foreground">{result.blurb}</p>
      </CardHeader>

      <CardContent className="space-y-6">
        {cert ? (
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Student" value={cert.student_name} />
            <Field label="Roll number" value={cert.roll_number} />
            <Field label="Programme" value={cert.programme} />
            <Field label="Year of passing" value={cert.year_of_passing} />
            <Field label="Grade" value={grade} />
            <Field label="Institution" value={`${cert.institution.name} (${cert.institution.code})`} />
            <Field label="Date of issue" value={cert.issue_date} />
            <Field label="Registry status" value={cert.status} />
          </dl>
        ) : (
          <p className="text-sm text-muted-foreground">
            No matching record is registered, so there are no certificate details to show.
          </p>
        )}

        <div>
          <h3 className="text-sm font-semibold">Checks</h3>
          <ul className="mt-1 divide-y">
            {verification.checks.map((check) => (
              <CheckRow key={check.name} check={check} />
            ))}
          </ul>
        </div>

        <p className="text-xs text-muted-foreground">
          Verification {verification.id} · {new Date(verification.created_at).toLocaleString()}
        </p>
      </CardContent>
    </Card>
  );
}
