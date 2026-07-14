import { useEffect, useRef, useState } from 'react';
import { deleteSignatureProfile, getSignaturePreview, getSignatureStatus, saveSignatureProfile, type SignatureStatus, type SignatureStroke } from '../services/signatureService';

const CANVAS_WIDTH = 700;
const CANVAS_HEIGHT = 260;

function drawStroke(ctx: CanvasRenderingContext2D, stroke: SignatureStroke) {
  if (!stroke.length) return;
  ctx.beginPath();
  ctx.moveTo(stroke[0].x * CANVAS_WIDTH, stroke[0].y * CANVAS_HEIGHT);
  for (const point of stroke.slice(1)) ctx.lineTo(point.x * CANVAS_WIDTH, point.y * CANVAS_HEIGHT);
  ctx.stroke();
}

export function SignatureSettingsPage({ setPage }: { setPage: (page: string) => void }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const startedAt = useRef(0);
  const [strokes, setStrokes] = useState<SignatureStroke[]>([]);
  const [drawing, setDrawing] = useState(false);
  const [status, setStatus] = useState<SignatureStatus | null>(null);
  const [preview, setPreview] = useState('');
  const [message, setMessage] = useState('');

  async function refresh() {
    const statusResponse = await getSignatureStatus();
    setStatus(statusResponse.data);
    const previewResponse = await getSignaturePreview();
    setPreview(previewResponse.data.preview_png_data_url || '');
  }

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    ctx.strokeStyle = '#111';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    strokes.forEach((stroke) => drawStroke(ctx, stroke));
  }, [strokes]);

  function pointFromEvent(event: React.PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
      t: Math.round(performance.now() - startedAt.current),
    };
  }

  function start(event: React.PointerEvent<HTMLCanvasElement>) {
    startedAt.current = performance.now();
    event.currentTarget.setPointerCapture(event.pointerId);
    setDrawing(true);
    setStrokes((current) => [...current, [pointFromEvent(event)]]);
  }

  function move(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawing) return;
    const point = pointFromEvent(event);
    setStrokes((current) => current.map((stroke, index) => index === current.length - 1 ? [...stroke, point] : stroke));
  }

  function stop() {
    setDrawing(false);
  }

  function clear() {
    setStrokes([]);
    setMessage('');
  }

  async function save() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const pointCount = strokes.reduce((sum, stroke) => sum + stroke.length, 0);
    if (pointCount < 20) {
      setMessage('Bitte die Signatur etwas laenger zeichnen.');
      return;
    }
    const result = await saveSignatureProfile({ canvas: { width: CANVAS_WIDTH, height: CANVAS_HEIGHT }, strokes, preview_png_data_url: canvas.toDataURL('image/png') });
    setMessage((result as { message?: string }).message || 'Signatur wurde lokal gespeichert.');
    await refresh();
  }

  async function remove() {
    await deleteSignatureProfile();
    setPreview('');
    setStatus(null);
    clear();
    await refresh();
    setMessage('Lokale Signatur wurde geloescht.');
  }

  async function testDraw() {
    setStrokes([
      Array.from({ length: 24 }, (_, index) => ({
        x: 0.16 + index * 0.03,
        y: 0.55 + Math.sin(index / 2) * 0.10,
        t: index * 12,
      })),
    ]);
    setMessage('Test-Signatur wurde gezeichnet. Speichern legt sie lokal ab.');
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Signatur verwalten</h1>
          <p>Die Signatur wird nur lokal gespeichert und nicht ins Repository uebernommen. Finales Signieren erfolgt nur nach ausdruecklicher Bestaetigung.</p>
        </div>
      </div>
      <section className="panel">
        <canvas
          ref={canvasRef}
          className="signature-pad"
          width={CANVAS_WIDTH}
          height={CANVAS_HEIGHT}
          onPointerDown={start}
          onPointerMove={move}
          onPointerUp={stop}
          onPointerCancel={stop}
        />
        <div className="actions">
          <button className="secondary" onClick={clear}>Loeschen</button>
          <button className="primary" onClick={save}>Signatur lokal speichern</button>
          <button className="secondary" onClick={testDraw}>Gespeicherte Signatur testen</button>
          <button className="secondary" onClick={() => setPage('dashboard')}>Zurueck</button>
        </div>
        {message && <div className="banner info">{message}</div>}
      </section>
      <section className="panel">
        <h2>Status</h2>
        <div className="small-cards">
          <div><span>Signatur gespeichert</span><strong>{status?.exists ? 'Ja' : 'Nein'}</strong></div>
          <div><span>Speicherort</span><strong>lokal</strong></div>
          <div><span>Format</span><strong>{status?.format || 'strokes + png/svg'}</strong></div>
          <div><span>Punkte</span><strong>{status?.point_count ?? 0}</strong></div>
        </div>
        {preview && <img className="signature-preview" src={preview} alt="Gespeicherte Signatur" />}
      </section>
    </>
  );
}
