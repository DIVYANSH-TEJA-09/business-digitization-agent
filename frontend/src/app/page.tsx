"use client";

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { uploadZip, getSamples, runSample } from '@/lib/api';
import type { SampleZip } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [samples, setSamples] = useState<SampleZip[]>([]);
  const [runningSample, setRunningSample] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getSamples()
      .then((data) => setSamples(data.samples))
      .catch(() => {});
  }, []);

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

  const handleRunSample = async (sample: SampleZip) => {
    setRunningSample(sample.filename);
    setError(null);
    try {
      const { job_id } = await runSample(sample.filename);
      router.push(`/processing/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run sample');
      setRunningSample(null);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const isLoading = isUploading || runningSample !== null;

  return (
    <main className="min-h-screen" style={{ background: 'var(--background)' }}>
      <div className="container mx-auto px-4 py-12 max-w-5xl">

        {/* ─── Hero Section ──────────────────────────────────── */}
        <div className="text-center mb-10">
          <div className="flex justify-center mb-4">
            <svg className="w-16 h-16" style={{ color: 'var(--primary)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-5xl font-bold mb-3" style={{ color: 'var(--foreground)' }}>Digi-Biz</h1>
          <p className="text-xl mb-1" style={{ color: 'var(--muted-foreground)' }}>Agentic Business Digitization Framework</p>
          <p className="text-sm" style={{ color: 'var(--muted-foreground)', opacity: 0.7 }}>
            Powered by 8 AI Agents &middot; Groq LLM &middot; Zero Manual Entry
          </p>
        </div>

        {/* ─── Upload Zone ───────────────────────────────────── */}
        <div className="mb-8">
          <div
            className="card p-10 text-center cursor-pointer border-2 border-dashed"
            style={{ borderColor: isLoading ? 'var(--primary)' : 'var(--border)' }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            onClick={() => !isLoading && fileInputRef.current?.click()}
          >
            <input ref={fileInputRef} type="file" accept=".zip" className="hidden" onChange={(e) => {
              if (e.target.files?.[0]) handleUpload(e.target.files[0]);
            }} disabled={isLoading} />

            {isLoading ? (
              <>
                <div className="animate-spin w-12 h-12 mx-auto mb-4" style={{ color: 'var(--primary)' }}>
                  <svg className="w-full h-full" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                </div>
                <p className="text-lg font-medium" style={{ color: 'var(--primary)' }}>
                  {runningSample ? `Processing sample...` : 'Uploading & Processing...'}
                </p>
              </>
            ) : (
              <>
                <svg className="w-14 h-14 mx-auto mb-4" style={{ color: 'var(--primary)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <h3 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground)' }}>Upload Your Business ZIP</h3>
                <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>Drag and drop or click to browse &middot; PDFs, DOCX, Images, Spreadsheets</p>
              </>
            )}
          </div>
          {error && <div className="mt-4 p-4 rounded-lg bg-red-50 border border-red-200"><p className="text-red-800">{error}</p></div>}
        </div>

        {/* ─── Sample Data for Evaluators ─────────────────────── */}
        {samples.length > 0 && (
          <div className="mb-10">
            <div className="text-center mb-5">
              <h2 className="text-xl font-bold" style={{ color: 'var(--foreground)' }}>🧪 Try a Sample</h2>
              <p className="text-sm mt-1" style={{ color: 'var(--muted-foreground)' }}>
                No files handy? Click below to see Digi-Biz in action instantly!
              </p>
            </div>
            <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(samples.length, 3)}, 1fr)` }}>
              {samples.map((sample) => (
                <button
                  key={sample.filename}
                  onClick={() => handleRunSample(sample)}
                  disabled={isLoading}
                  className="card p-5 text-left transition-all duration-200 hover:shadow-lg border-2"
                  style={{
                    borderColor: runningSample === sample.filename ? 'var(--primary)' : 'transparent',
                    opacity: isLoading && runningSample !== sample.filename ? 0.5 : 1,
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">📦</span>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-bold truncate" style={{ color: 'var(--foreground)' }}>{sample.name}</h4>
                      <p className="text-xs mt-1" style={{ color: 'var(--muted-foreground)' }}>{sample.size_mb} MB &middot; Click to process</p>
                    </div>
                    <svg className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--primary)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ─── How It Works ──────────────────────────────────── */}
        <div className="mb-10">
          <h2 className="text-2xl font-bold text-center mb-6" style={{ color: 'var(--foreground)' }}>How It Works</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="card p-6 text-center">
              <div className="text-4xl mb-3">📄</div>
              <h4 className="font-bold mb-2" style={{ color: 'var(--foreground)' }}>1. Upload Documents</h4>
              <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>ZIP containing PDFs, DOCX, images, menus, price lists — any business documents</p>
            </div>
            <div className="card p-6 text-center">
              <div className="text-4xl mb-3">🤖</div>
              <h4 className="font-bold mb-2" style={{ color: 'var(--foreground)' }}>2. AI Processing</h4>
              <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>8 specialized AI agents parse, extract tables, analyze images, and map data to schemas</p>
            </div>
            <div className="card p-6 text-center">
              <div className="text-4xl mb-3">✨</div>
              <h4 className="font-bold mb-2" style={{ color: 'var(--foreground)' }}>3. Get Profile</h4>
              <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>Receive a beautiful, structured digital business profile you can edit and export</p>
            </div>
          </div>
        </div>

        {/* ─── AI Pipeline Details ───────────────────────────── */}
        <div className="mb-10">
          <h2 className="text-2xl font-bold text-center mb-6" style={{ color: 'var(--foreground)' }}>🧠 The AI Pipeline</h2>
          <div className="grid md:grid-cols-4 gap-4">
            {[
              { icon: '🔍', name: 'File Discovery', desc: 'ZIP extraction & file classification' },
              { icon: '📝', name: 'Doc Parsing', desc: 'Text extraction from PDFs & DOCX' },
              { icon: '📊', name: 'Table Extraction', desc: 'Detect & structure tabular data' },
              { icon: '🖼️', name: 'Media Analysis', desc: 'Image extraction & vision AI' },
              { icon: '🗂️', name: 'Indexing', desc: 'Build searchable keyword index' },
              { icon: '🧬', name: 'Schema Mapping', desc: 'LLM extracts structured fields' },
              { icon: '✅', name: 'Validation', desc: 'Quality scoring & completeness' },
              { icon: '📦', name: 'Profile Output', desc: 'JSON profile ready to use' },
            ].map((step) => (
              <div key={step.name} className="card p-4 text-center">
                <div className="text-2xl mb-2">{step.icon}</div>
                <h5 className="font-semibold text-sm mb-1" style={{ color: 'var(--foreground)' }}>{step.name}</h5>
                <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ─── Supported Businesses ──────────────────────────── */}
        <div className="mb-10">
          <h2 className="text-2xl font-bold text-center mb-6" style={{ color: 'var(--foreground)' }}>🎯 Works For Any Business</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { emoji: '🍽️', name: 'Restaurants', desc: 'Menus, dishes, prices' },
              { emoji: '🏪', name: 'Retail', desc: 'Products, inventory' },
              { emoji: '💼', name: 'Services', desc: 'Packages, pricing' },
              { emoji: '🏨', name: 'Hotels', desc: 'Rooms, amenities, rates' },
              { emoji: '🥾', name: 'Travel & Treks', desc: 'Tours, itineraries' },
              { emoji: '🏥', name: 'Healthcare', desc: 'Services, specialties' },
            ].map((biz) => (
              <div key={biz.name} className="card p-4 flex items-center gap-3">
                <span className="text-2xl">{biz.emoji}</span>
                <div>
                  <h5 className="font-semibold text-sm" style={{ color: 'var(--foreground)' }}>{biz.name}</h5>
                  <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>{biz.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ─── Tech Stack ────────────────────────────────────── */}
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--foreground)' }}>🔧 Tech Stack</h2>
          <div className="flex flex-wrap justify-center gap-3">
            {['Next.js', 'FastAPI', 'Groq LLM', 'Llama 3.1', 'Pydantic', 'pdfplumber', 'Pillow', 'Docker'].map((tech) => (
              <span key={tech} className="px-3 py-1.5 rounded-full text-xs font-medium" style={{
                background: 'var(--accent)',
                color: 'var(--accent-foreground)',
              }}>
                {tech}
              </span>
            ))}
          </div>
        </div>

        {/* ─── Footer ────────────────────────────────────────── */}
        <div className="text-center pt-6 border-t" style={{ borderColor: 'var(--border)' }}>
          <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
            Built with ❤️ &middot; Agentic AI-powered Business Digitization
          </p>
        </div>
      </div>
    </main>
  );
}
