import { Camera, FileCheck2, FileUp, Loader2 } from 'lucide-react';
import { useId, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { UPLOAD_ACCEPT, UPLOAD_MAX_BYTES } from '@/hooks/useVerify';
import { cn } from '@/lib/utils';

const ACCEPTED_TYPES = new Set(UPLOAD_ACCEPT.split(','));

function describeSize(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} kB`;
}

/**
 * Reject what we can see is wrong before spending an upload on it.
 *
 * This is a courtesy, not a control: the server decides the real type from the
 * file's own bytes, because a filename and a browser-reported MIME type are
 * both trivially wrong.
 */
function localComplaint(file: File): string | null {
  if (file.size === 0) return 'That file is empty.';
  if (file.size > UPLOAD_MAX_BYTES) {
    return `That file is ${describeSize(file.size)}. The limit is ${describeSize(UPLOAD_MAX_BYTES)}.`;
  }
  // An empty `type` means the browser could not tell; let the server decide.
  if (file.type && !ACCEPTED_TYPES.has(file.type)) {
    return 'Only PDF, PNG and JPEG files can be verified.';
  }
  return null;
}

interface Props {
  onFile: (file: File) => void;
  disabled?: boolean;
  busy?: boolean;
  busyLabel?: string;
  /** Name of the file already submitted, shown while the job runs. */
  submittedName?: string;
}

export default function UploadDropzone({
  onFile,
  disabled = false,
  busy = false,
  busyLabel = 'Working…',
  submittedName,
}: Props) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [complaint, setComplaint] = useState<string | null>(null);

  const accept = (file: File | undefined) => {
    if (!file) return;
    const problem = localComplaint(file);
    setComplaint(problem);
    if (!problem) onFile(file);
  };

  const pick = () => inputRef.current?.click();
  // A separate input, because `capture` must not be set on the file picker:
  // on a phone it would hide the gallery and the files, and on a desktop
  // browser it is ignored anyway.
  const photograph = () => cameraRef.current?.click();

  return (
    <div className="space-y-3">
      <div
        // A label, so a click or a keyboard activation opens the file picker
        // without re-implementing either.
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled && !busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (disabled || busy) return;
          accept(e.dataTransfer.files?.[0]);
        }}
        className={cn(
          'rounded-lg border-2 border-dashed p-8 text-center transition-colors',
          dragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25',
          (disabled || busy) && 'opacity-60',
        )}
      >
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={UPLOAD_ACCEPT}
          className="sr-only"
          disabled={disabled || busy}
          onChange={(e) => {
            accept(e.target.files?.[0]);
            // Reset, so choosing the same file again still fires onChange.
            e.target.value = '';
          }}
        />

        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="sr-only"
          disabled={disabled || busy}
          onChange={(e) => {
            accept(e.target.files?.[0]);
            e.target.value = '';
          }}
        />

        {busy ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
            <p className="text-sm font-medium" role="status">
              {busyLabel}
            </p>
            {submittedName && (
              <p className="max-w-full truncate text-xs text-muted-foreground">{submittedName}</p>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            {submittedName ? (
              <FileCheck2 className="h-8 w-8 text-muted-foreground" aria-hidden />
            ) : (
              <FileUp className="h-8 w-8 text-muted-foreground" aria-hidden />
            )}
            <p className="text-sm font-medium">
              Drag a certificate here, or{' '}
              <Button
                type="button"
                variant="link"
                className="h-auto p-0 text-sm"
                onClick={pick}
                disabled={disabled}
              >
                choose a file
              </Button>
            </p>
            <Button type="button" variant="outline" size="sm" onClick={photograph} disabled={disabled}>
              <Camera />
              Take a photo
            </Button>
            <p className="text-xs text-muted-foreground">
              PDF, PNG or JPEG, up to {describeSize(UPLOAD_MAX_BYTES)}. A PDF with a text layer is
              read directly; a photo or scan has its QR code read first, then its printed text.
            </p>
          </div>
        )}
      </div>

      {complaint && (
        <p className="text-sm text-destructive" role="alert">
          {complaint}
        </p>
      )}
    </div>
  );
}
