import { Upload } from 'lucide-react';

export function FileUpload({ onFile }: { onFile: (file: File) => void }) {
  return (
    <label className="drop-zone">
      <Upload size={28} />
      <strong>Datei hochladen</strong>
      <span>PDF, PPTX, PPT, HTML, Markdown oder TXT</span>
      <input type="file" accept=".pdf,.pptx,.ppt,.html,.htm,.md,.txt" onChange={(event) => event.target.files?.[0] && onFile(event.target.files[0])} />
    </label>
  );
}
