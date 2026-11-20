import { CheckCircle2, CircleHelp, MinusCircle, Printer, XCircle } from 'lucide-react';

import DocumentMatch from '@/components/DocumentMatch';
import ExtractedFieldsTable from '@/components/ExtractedFieldsTable';
import VerificationRequests from '@/components/VerificationRequests';
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
  // Same verdict, different reason: something on the page disagrees with the
  // registry, but not clearly enough to call it a conflict. Saying "needs
  // review" alone would hide the one fact the verifier must act on.
  MANUAL_REVIEW_DISCREPANCY: {
    label: 'Possible discrepancy',
    explanation:
      'A printed value does not match the registry, but it was not read clearly enough to be certain. Check the difference below against the document in your hand, and ask the issuing institution to confirm.',
    banner: 'border-amber-300 bg-amber-50 text-amber-900',
    badge: 'bg-amber-600 text-white',
  },
  // A genuine record reached through a genuine QR, beside a document whose
  // printed content could not be checked against it. Calling that "Verified"
  // told the verifier the paper in their hand was fine, which nothing had
  // established.
  MANUAL_REVIEW_UNCONFIRMED: {
    label: 'Unconfirmed',
    explanation:
      'QR code is genuine — document content could not be confirmed. The QR points to a real record, but the printed details on this document could not be checked against it. Compare the document with the issued details below, or request confirmation from the institution.',
    banner: 'border-amber-300 bg-amber-50 text-amber-900',
    badge: 'bg-amber-600 text-white',
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
  document_content: 'Document contents',
};

const FIELD_LABELS: Record<string, string> = {
  cert_number: 'certificate number',
  roll_number: 'roll number',
  student_name: 'student',
  programme: 'programme',
  year_of_passing: 'year of passing',
  cgpa: 'CGPA',
  marks: 'marks',
  issue_date: 'date of issue',
};

/** The engine emits one check per field as `field_match.<field>`. */
function checkLabel(name: string): string {
  if (name.startsWith('field_match.')) {
    const field = name.slice('field_match.'.length);
    return `Field match — ${FIELD_LABELS[field] ?? field}`;
  }
  return CHECK_LABELS[name] ?? name;
}

function statusOf(verification: Verification, name: string): string | undefined {
  return verification.checks.find((c) => c.name === name)?.status;
}

/** Field comparisons that actually happened, with how many of them agreed. */
function tally(verification: Verification): { matched: number; compared: number } {
  const fields = verification.checks.filter((c) => c.name.startsWith('field_match.') && c.state);
  return {
    matched: fields.filter((c) => c.state === 'matches').length,
    compared: fields.length,
  };
}

/**
 * The record is genuine; the document presented is what could not be confirmed.
 *
 * Read off the engine's `document_content` check rather than re-derived here:
 * the bar (the name read and matched, enough fields matching, nothing
 * differing) is the engine's rule, and the page must not hold a second,
 * drifting copy of it.
 */
function isUnconfirmed(verification: Verification): boolean {
  if (verification.result !== 'MANUAL_REVIEW') return false;
  if (statusOf(verification, 'document_content') !== 'uncertain') return false;
  // A value that disagrees is a discrepancy, which says more and wins.
  if (verification.checks.some((c) => c.name.startsWith('field_match.') && c.state === 'differs')) {
    return false;
  }
  const numberMatched = verification.checks.some(
    (c) => c.name === 'field_match.cert_number' && c.state === 'matches',
  );
  return statusOf(verification, 'qr_signature') === 'pass' || numberMatched;
}

/**
 * Which evidence actually carried the result, said plainly.
 *
 * Derived from the checks rather than sent as its own field: the decision
 * rules in `verification/engine.py` turn on exactly these checks, so a
 * sentence read off them cannot drift out of step with the verdict.
 */
function pathUsed(verification: Verification, unconfirmed: boolean): string | null {
  if (verification.method !== 'upload') return null;
  const compared = verification.checks.some(
    (c) => c.name.startsWith('field_match.') && c.status === 'pass',
  );
  const verb = verification.result === 'VERIFIED' ? 'Verified' : 'Checked';

  if (statusOf(verification, 'file_hash') === 'pass') {
    return `${verb} by the file itself — these are the exact bytes the institution issued.`;
  }
  if (unconfirmed) {
    const { matched, compared: total } = tally(verification);
    const counted = total ? `${matched} of ${total} fields matched` : 'no printed details were read';
    return statusOf(verification, 'qr_signature') === 'pass'
      ? `Signed QR verified; printed text not confirmed (${counted}).`
      : `Certificate number matched; printed text not confirmed (${counted}).`;
  }
  if (statusOf(verification, 'qr_signature') === 'pass') {
    return `${verb} by the signed QR code on the document; its printed text was read as a cross-check.`;
  }
  if (compared) {
    return `${verb} by reading the printed text — no signed QR could be read from this document.`;
  }
  return 'Neither a signed QR nor a known layout could be read from this document, so nothing was decided from it.';
}

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
          {checkLabel(check.name)}
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
  /** Open the "ask the institution" dialog. Only the result page passes it. */
  onRequestConfirmation?: () => void;
}

export default function VerificationResult({
  verification,
  full = false,
  onRequestConfirmation,
}: Props) {
  // A review caused by a value that disagrees is announced as such.
  const differs = verification.checks.some(
    (c) => c.name.startsWith('field_match.') && c.state === 'differs',
  );
  const unconfirmed = isUnconfirmed(verification);
  const key =
    verification.result === 'MANUAL_REVIEW' && differs
      ? 'MANUAL_REVIEW_DISCREPANCY'
      : unconfirmed
        ? 'MANUAL_REVIEW_UNCONFIRMED'
        : verification.result;
  const result = RESULTS[key] ?? {
    label: verification.result,
    explanation: '',
    banner: 'border-zinc-200 bg-zinc-100 text-zinc-900',
    badge: 'bg-zinc-600 text-white',
  };
  const cert = verification.certificate;
  const path = pathUsed(verification, unconfirmed);
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
        {path && <p className="mt-2 max-w-3xl text-sm font-medium">{path}</p>}
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

      <DocumentMatch verification={verification} />

      <ExtractedFieldsTable verification={verification} />

      {onRequestConfirmation && (
        <VerificationRequests verification={verification} onRequest={onRequestConfirmation} />
      )}

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
