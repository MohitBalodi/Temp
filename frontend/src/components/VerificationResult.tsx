import { CheckCircle2, CircleHelp, MinusCircle, Printer, XCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Verification, VerificationCheck } from '@/hooks/useVerify';
import { cn } from '@/lib/utils';

/** Wording and colour per result. Never "fake" or "forged": absence of evidence
 * is not fraud, so an unknown record reads as "needs review". */
const RESULTS: Record<
  string,
  { label: string; explanation: string; banner: string; badge: string }
> = {
  VERIFIED: {
    label: 'Verified',
    explanation:
      'This certificate is in the issuing institution’s registry and its signature matches that institution’s key. The details below are what the institution recorded.',
    banner: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    badge: 'bg-emerald-600 text-white',
  },
  MISMATCH: {
    label: 'Mismatch',
    explanation:
      'What was presented does not agree with the registry record. This is not proof of forgery — a reprint, a typo or an edited copy can cause it. Ask the issuing institution to confirm.',
    banner: 'border-red-200 bg-red-50 text-red-900',
    badge: 'bg-red-600 text-white',
  },
  MANUAL_REVIEW: {
    label: 'Needs review',
    explanation:
      'No matching record — this is not proof of forgery; the issuing institution should confirm.',
    banner: 'border-amber-200 bg-amber-50 text-amber-900',
    badge: 'bg-amber-500 text-white',
  },
  REVOKED: {
    label: 'Revoked',
    explanation:
      'The issuing institution has withdrawn this certificate. It was issued, but the institution no longer stands behind it.',
    banner: 'border-zinc-200 bg-zinc-100 text-zinc-900',
    badge: 'bg-zinc-600 text-white',
  },
};

const CHECK_ICONS = {
  pass: { Icon: CheckCircle2, className: 'text-emerald-600', label: 'passed' },
  fail: { Icon: XCircle, className: 'text-red-600', label: 'failed' },
  skipped: { Icon: MinusCircle, className: 'text-muted-foreground', label: 'not applicable' },
  uncertain: { Icon: CircleHelp, className: 'text-amber-500', label: 'uncertain' },
} as const;

const CHECK_LABELS: Record<string, string> = {
  registry_lookup: 'Registry lookup',
  revocation: 'Revocation',
  record_signature: 'Registry signature',
  qr_signature: 'QR signature',
  file_hash: 'File hash',
  field_match: 'Field match',
};

const METHOD_LABELS: Record<string, string> = {
  id: 'Certificate number',
  qr: 'QR code',
  upload: 'Uploaded document',
};

function CheckRow({ check }: { check: VerificationCheck }) {
  const { Icon, className, label } =
    CHECK_ICONS[check.status as keyof typeof CHECK_ICONS] ?? CHECK_ICONS.skipped;
  return (
    <li className="print-keep flex gap-3 py-3">
      <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', className)} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">
          {CHECK_LABELS[check.name] ?? check.name}
          <span className="sr-only"> — {label}</span>
        </p>
        <p className="text-sm text-muted-foreground">{check.detail}</p>
      </div>
      <span className="shrink-0 text-xs uppercase tracking-wide text-muted-foreground">
        {check.status}
      </span>
    </li>
  );
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === '') return null;
  return (
    <div className="print-keep">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{value}</dd>
    </div>
  );
}

interface Props {
  verification: Verification;
  /** Show the banner, the audit trail and the print button (the result page). */
  full?: boolean;
}

export default function VerificationResult({ verification, full = false }: Props) {
  const result = RESULTS[verification.result] ?? {
    label: verification.result,
    explanation: '',
    banner: 'border-zinc-200 bg-zinc-100 text-zinc-900',
    badge: 'bg-zinc-600 text-white',
  };
  const cert = verification.certificate;
  const number = cert?.cert_number ?? verification.extracted_fields?.cert_number ?? '—';
  const grade = [cert?.cgpa && `CGPA ${cert.cgpa}`, cert?.marks && `${cert.marks}%`]
    .filter(Boolean)
    .join(' / ');

  return (
    <div className="space-y-6">
      <div className={cn('rounded-lg border p-5', result.banner)}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={cn(
                'rounded-md px-3 py-1 text-sm font-semibold uppercase tracking-wide',
                result.badge,
              )}
              role="status"
            >
              {result.label}
            </span>
            <span className="font-mono text-base font-semibold">{number}</span>
          </div>
          {full && (
            <Button variant="outline" size="sm" className="print:hidden" onClick={() => window.print()}>
              <Printer />
              Print / Save as PDF
            </Button>
          )}
        </div>
        <p className="mt-3 max-w-3xl text-sm">{result.explanation}</p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Certificate details</CardTitle>
        </CardHeader>
        <CardContent>
          {cert ? (
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Student" value={cert.student_name} />
              <Field label="Roll number" value={cert.roll_number} />
              <Field label="Programme" value={cert.programme} />
              <Field label="Year of passing" value={cert.year_of_passing} />
              <Field label="Grade" value={grade} />
              <Field
                label="Institution"
                value={`${cert.institution.name} (${cert.institution.code})`}
              />
              <Field label="Date of issue" value={cert.issue_date} />
              <Field label="Registry status" value={cert.status} />
              <Field label="Issued file SHA-256" value={cert.file_sha256} />
            </dl>
          ) : (
            <p className="text-sm text-muted-foreground">
              No matching record is registered, so there are no certificate details to show.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-1">
          <CardTitle className="text-base">Checks</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y">
            {verification.checks.map((check) => (
              <CheckRow key={check.name} check={check} />
            ))}
          </ul>
        </CardContent>
      </Card>

      {full && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">This verification</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Field
                label="Method"
                value={METHOD_LABELS[verification.method] ?? verification.method}
              />
              <Field label="Checked at" value={new Date(verification.created_at).toLocaleString()} />
              <Field label="Verified by" value={verification.verifier?.email} />
              <Field label="Verification ID" value={verification.id} />
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
