import { Html5Qrcode } from 'html5-qrcode';
import { Camera, CameraOff, Image as ImageIcon } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';

const REGION_ID = 'qr-reader';

interface Props {
  /** Called with the decoded text. The camera stops first, so one scan is one
   * verification rather than a stream of them. */
  onDecoded: (text: string) => void;
  disabled?: boolean;
}

export default function QrScanner({ onDecoded, disabled }: Props) {
  const scanner = useRef<Html5Qrcode | null>(null);
  const [cameraOn, setCameraOn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const instance = () => (scanner.current ??= new Html5Qrcode(REGION_ID));

  const stopCamera = async () => {
    const current = scanner.current;
    if (current?.isScanning) {
      try {
        await current.stop();
      } catch {
        // Already stopped, or the element went away with the page.
      }
    }
    setCameraOn(false);
  };

  // Leave no camera running behind when the verifier navigates away.
  useEffect(() => {
    return () => {
      void stopCamera();
    };
  }, []);

  const startCamera = async () => {
    setError(null);
    try {
      const current = instance();
      try {
        current.clear(); // drop a previously scanned still image
      } catch {
        // Nothing to clear.
      }
      await current.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: 250 },
        (text) => {
          void stopCamera();
          onDecoded(text);
        },
        undefined,
      );
      setCameraOn(true);
    } catch {
      setError('Could not open the camera. Allow camera access, or scan a saved image instead.');
      setCameraOn(false);
    }
  };

  const scanImage = async (file: File) => {
    setError(null);
    await stopCamera();
    try {
      onDecoded(await instance().scanFile(file, true));
    } catch {
      setError('No QR code could be read from that image.');
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {cameraOn ? (
          <Button variant="outline" onClick={() => void stopCamera()}>
            <CameraOff />
            Stop camera
          </Button>
        ) : (
          <Button variant="outline" onClick={() => void startCamera()} disabled={disabled}>
            <Camera />
            Start camera
          </Button>
        )}
        <Button
          variant="outline"
          onClick={() => fileInput.current?.click()}
          disabled={disabled}
        >
          <ImageIcon />
          Scan an image
        </Button>
        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          className="sr-only"
          aria-label="QR code image"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = ''; // allow re-picking the same file
            if (file) void scanImage(file);
          }}
        />
      </div>

      <div
        id={REGION_ID}
        className="mx-auto w-full max-w-sm overflow-hidden rounded-md border bg-muted/30"
      />

      {!cameraOn && (
        <p className="text-xs text-muted-foreground">
          The camera needs a secure page (localhost counts) and your permission. You can also
          upload a photo or screenshot of the QR code.
        </p>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
