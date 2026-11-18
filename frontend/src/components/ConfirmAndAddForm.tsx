import { useState, type FormEvent } from 'react';

import { apiErrorMessage, apiFieldErrors } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { Decision } from '@/hooks/useReviews';

const EMPTY = {
  cert_number: '',
  student_name: '',
  roll_number: '',
  programme: '',
  year_of_passing: '',
  cgpa: '',
  marks: '',
  issue_date: '',
};

type FormState = typeof EMPTY;

const FIELDS: { name: keyof FormState; label: string; type?: string; hint?: string }[] = [
  { name: 'cert_number', label: 'Certificate number' },
  { name: 'student_name', label: 'Student name' },
  { name: 'roll_number', label: 'Roll number' },
  { name: 'programme', label: 'Programme' },
  { name: 'year_of_passing', label: 'Year of passing', type: 'number' },
  { name: 'issue_date', label: 'Issue date', type: 'date' },
  { name: 'cgpa', label: 'CGPA (0–10)', type: 'number', hint: 'CGPA or marks, at least one' },
  { name: 'marks', label: 'Marks (%)', type: 'number' },
];

/**
 * "Confirm & add to registry": the certificate as the institution states it.
 *
 * Prefilled from what the document said, and every field editable — the OCR's
 * reading is a draft, not a source of truth, and the institution is the one
 * that knows. Submitting runs the ordinary create service, so the row is
 * signed with the institution's key and gets its issued PDF like any other.
 */
export default function ConfirmAndAddForm({
  prefill,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  prefill: Record<string, string>;
  pending: boolean;
  error: unknown;
  onSubmit: (decision: Decision) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => ({
    ...EMPTY,
    // Only keys the form has: the extraction may carry others (institution
    // code, the issue date it found) that this form does not ask for.
    ...Object.fromEntries(Object.keys(EMPTY).map((k) => [k, prefill[k] ?? ''])),
  }));

  const fieldErrors = error ? apiFieldErrors(error) : {};
  const formError = error
    ? (fieldErrors._form ?? (Object.keys(fieldErrors).length ? undefined : apiErrorMessage(error)))
    : undefined;

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      decision: 'confirmed_added',
      certificate: {
        cert_number: form.cert_number,
        student_name: form.student_name,
        roll_number: form.roll_number,
        programme: form.programme,
        year_of_passing: Number(form.year_of_passing),
        cgpa: form.cgpa || null,
        marks: form.marks || null,
        issue_date: form.issue_date,
      },
    });
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <p className="text-sm text-muted-foreground">
        Check every value against your own records before confirming. This creates a signed
        registry record and issues its PDF, exactly as adding a certificate does — the values
        below are only what was read off the document.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {FIELDS.map((field) => (
          <div key={field.name} className="space-y-1.5">
            <Label htmlFor={`add-${field.name}`}>{field.label}</Label>
            <Input
              id={`add-${field.name}`}
              type={field.type ?? 'text'}
              step={field.type === 'number' && field.name !== 'year_of_passing' ? '0.01' : undefined}
              required={field.name !== 'cgpa' && field.name !== 'marks'}
              value={form[field.name]}
              onChange={(e) => setForm({ ...form, [field.name]: e.target.value })}
              autoComplete="off"
            />
            {fieldErrors[field.name] ? (
              <p className="text-xs text-destructive">{fieldErrors[field.name]}</p>
            ) : (
              field.hint && <p className="text-xs text-muted-foreground">{field.hint}</p>
            )}
          </div>
        ))}
      </div>

      {formError && (
        <p className="text-sm text-destructive" role="alert">
          {formError}
        </p>
      )}

      <div className="flex gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? 'Adding…' : 'Confirm & add to registry'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={pending}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
