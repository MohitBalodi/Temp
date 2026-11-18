import { CheckCircle2, CircleHelp, XCircle } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Verification } from '@/hooks/useVerify';
import { cn } from '@/lib/utils';

/** One extracted field as the backend stores it in `extracted_fields.fields`. */
interface ExtractedField {
  name: string;
  value: string | null;
  raw: string;
  confidence: number;
}

const FIELD_LABELS: Record<string, string> = {
  cert_number: 'Certificate number',
  roll_number: 'Roll number',
  student_name: 'Student',
  programme: 'Programme',
  year_of_passing: 'Year of passing',
  cgpa: 'CGPA',
  marks: 'Marks',
  issue_date: 'Date of issue',
  institution_code: 'Institution code',
};

/**
 * The fields a verdict may turn on. One of these that the reader missed still
 * gets a row — with the registry's value and "not checked" — because a silent
 * omission reads as if the field had agreed.
 */
const CRITICAL_FIELDS = [
  'cert_number',
  'student_name',
  'roll_number',
  'programme',
  'year_of_passing',
  'cgpa',
  'marks',
];

/** Order shown to the verifier: the critical fields first, in spec order. */
const FIELD_ORDER = [
  'cert_number',
  'student_name',
  'roll_number',
  'programme',
  'year_of_passing',
  'cgpa',
  'marks',
  'issue_date',
  'institution_code',
];

const SOURCE_LABELS: Record<string, string> = {
  pdf_text_layer: 'read directly from the PDF’s text layer (exact, not OCR)',
  ocr: 'read by OCR from the page image',
  none: 'no text could be read',
};

function fieldsOf(verification: Verification): Record<string, ExtractedField> {
  const extracted = verification.extracted_fields as
    | { fields?: Record<string, ExtractedField> }
    | null
    | undefined;
  return extracted?.fields ?? {};
}

/**
 * The registry's value for a field, in the same shape the comparison used, so
 * the two columns are genuinely comparable rather than merely adjacent.
 */
function registryValue(verification: Verification, name: string): string | null {
  const cert = verification.certificate;
  if (!cert) return null;
  switch (name) {
    case 'cert_number':
      return cert.cert_number;
    case 'roll_number':
      return cert.roll_number;
    case 'student_name':
      return cert.student_name;
    case 'programme':
      return cert.programme;
    case 'year_of_passing':
      return String(cert.year_of_passing);
    case 'cgpa':
      return cert.cgpa ?? null;
    case 'marks':
      return cert.marks ?? null;
    case 'issue_date':
      return cert.issue_date;
    case 'institution_code':
      return cert.institution.code;
    default:
      return null;
  }
}

/** The per-field check the engine recorded, e.g. `field_match.cgpa`. */
function statusOf(verification: Verification, name: string): string | null {
  const check = verification.checks.find((c) => c.name === `field_match.${name}`);
  return check?.status ?? null;
}

const STATUS_STYLES = {
  pass: { Icon: CheckCircle2, className: 'text-emerald-600', label: 'matches' },
  fail: { Icon: XCircle, className: 'text-red-600', label: 'conflicts' },
  uncertain: { Icon: CircleHelp, className: 'text-amber-500', label: 'uncertain' },
} as const;

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percent = Math.round(confidence * 100);
  // Mirrors OCR_MIN_FIELD_CONFIDENCE; a reading below it cannot cause a
  // mismatch, so it is worth showing the verifier why.
  const low = confidence < 0.85;
  return (
    <span
      className={cn(
        'rounded px-1.5 py-0.5 text-xs font-medium tabular-nums',
        low ? 'bg-amber-100 text-amber-900' : 'bg-muted text-muted-foreground',
      )}
      title={low ? 'Below the confidence threshold, so it cannot count as a conflict' : undefined}
    >
      {percent}%
    </span>
  );
}

export default function ExtractedFieldsTable({ verification }: { verification: Verification }) {
  const extracted = verification.extracted_fields as
    | { template?: string | null; text_source?: string; ocr_engine?: string | null }
    | null
    | undefined;
  const fields = fieldsOf(verification);
  const names = FIELD_ORDER.filter(
    (n) =>
      n in fields ||
      // A critical field the registry holds and the reader did not find.
      (CRITICAL_FIELDS.includes(n) && registryValue(verification, n) !== null),
  );

  if (verification.method !== 'upload') return null;

  const source = extracted?.text_source ?? 'none';
  const template = extracted?.template;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">What the document says</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          The values below were {SOURCE_LABELS[source] ?? source}
          {template ? ` using the “${template}” layout` : ', and no known layout matched'}.
          {source === 'ocr' && ' A percentage is how sure the reader was of that value.'}
        </p>

        {names.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No fields could be read from this document, so nothing was compared against the
            registry. That is why the result asks for review rather than deciding.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Field</th>
                  <th className="py-2 pr-4 font-medium">On the document</th>
                  <th className="py-2 pr-4 font-medium">In the registry</th>
                  <th className="py-2 font-medium">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {names.map((name) => {
                  const field = fields[name];
                  const expected = registryValue(verification, name);
                  const status = statusOf(verification, name);
                  const style = status ? STATUS_STYLES[status as keyof typeof STATUS_STYLES] : null;
                  return (
                    <tr key={name} className="print-keep align-top">
                      <td className="py-2 pr-4 font-medium">{FIELD_LABELS[name] ?? name}</td>
                      <td className="py-2 pr-4">
                        {field ? (
                          <div className="flex flex-wrap items-center gap-2">
                            {/* `raw` keeps the document's own casing; `value`
                                is the normalized form that was compared. */}
                            <span className="font-mono">{field.raw || field.value || '—'}</span>
                            {source === 'ocr' && <ConfidenceBadge confidence={field.confidence} />}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">could not be read</span>
                        )}
                      </td>
                      <td className="py-2 pr-4 font-mono text-muted-foreground">
                        {expected ?? '—'}
                      </td>
                      <td className="py-2">
                        {style ? (
                          <span className={cn('flex items-center gap-1.5', style.className)}>
                            <style.Icon className="h-4 w-4 shrink-0" aria-hidden />
                            <span className="text-xs">{style.label}</span>
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">not checked</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
