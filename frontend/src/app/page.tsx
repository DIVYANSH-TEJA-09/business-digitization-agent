"use client";

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { uploadZip } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith('.zip')) {
      setError('Please upload a ZIP file');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const { job_id } = await uploadZip(file);
      router.push(`/processing/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setIsUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  return (
    <main className="min-h-screen" style={{ background: 'var(--background)' }}>
      <div className="container mx-auto px-4 py-16 max-w-4xl">
        <div className="text-center mb-12">
          <div className="flex justify-center mb-4">
            <svg className="w-16 h-16" style={{ color: 'var(--primary)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-5xl font-bold mb-4" style={{ color: 'var(--foreground)' }}>Digi-Biz</h1>
          <p className="text-xl mb-2" style={{ color: 'var(--muted-foreground)' }}>Agentic Business Digitization Framework</p>
        </div>

        <div className="mb-8">
          <div
            className="card p-12 text-center cursor-pointer border-2 border-dashed"
            style={{ borderColor: isUploading ? 'var(--primary)' : 'var(--border)' }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input ref={fileInputRef} type="file" accept=".zip" className="hidden" onChange={(e) => {
              if (e.target.files?.[0]) handleUpload(e.target.files[0]);
            }} disabled={isUploading} />
            
            {isUploading ? (
              <><div className="animate-spin w-12 h-12 mx-auto mb-4" style={{ color: 'var(--primary)' }}><svg className="w-full h-full" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg></div><p className="text-lg font-medium" style={{ color: 'var(--primary)' }}>Uploading & Processing...</p></>
            ) : (
              <><svg className="w-16 h-16 mx-auto mb-4" style={{ color: 'var(--primary)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg><h3 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground)' }}>Upload Your Business ZIP</h3><p className="text-base mb-4" style={{ color: 'var(--muted-foreground)' }}>Drag and drop or click to browse</p></>
            )}
          </div>
          {error && <div className="mt-4 p-4 rounded-lg bg-red-50 border border-red-200"><p className="text-red-800">{error}</p></div>}
        </div>

        <div className="grid md:grid-cols-3 gap-6 mt-12">
          <div className="card p-6 text-center"><div className="text-4xl mb-3">📄</div><h4 className="font-bold mb-2" style={{ color: 'var(--foreground)' }}>Upload Documents</h4><p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>ZIP with PDFs, images, menus</p></div>
          <div className="card p-6 text-center"><div className="text-4xl mb-3">🤖</div><h4 className="font-bold mb-2" style={{ color: 'var(--foreground)' }}>AI Processing</h4><p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>AI extracts info & services</p></div>
          <div className="card p-6 text-center"><div className="text-4xl mb-3">✨</div><h4 className="font-bold mb-2" style={{ color: 'var(--foreground)' }}>Get Profile</h4><p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>Beautiful digital profile</p></div>
        </div>
      </div>
    </main>
  );
}
