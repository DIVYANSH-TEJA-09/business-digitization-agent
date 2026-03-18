"use client";

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getJobStatus } from '@/lib/api';

const PHASES: Record<string, { label: string; icon: string }> = {
  upload: { label: 'Uploading ZIP', icon: '📁' },
  file_discovery: { label: 'Discovering Files', icon: '🔍' },
  document_parsing: { label: 'Parsing Documents', icon: '📄' },
  table_extraction: { label: 'Extracting Tables', icon: '📊' },
  media_extraction: { label: 'Extracting Images', icon: '🖼️' },
  indexing: { label: 'Building Index', icon: '🔍' },
  schema_mapping: { label: 'Generating Profile', icon: '🤖' },
  done: { label: 'Complete!', icon: '✅' },
};

export default function ProcessingPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.job_id as string;
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const data = await getJobStatus(jobId);
        setStatus(data);
        if (data.status === 'completed') {
          setTimeout(() => router.push(`/profile/${jobId}`), 1000);
        } else if (data.status === 'failed') {
          setError(data.error || 'Processing failed');
        }
      } catch (err) {
        setError('Failed to get status');
      }
    };
    const interval = setInterval(pollStatus, 2000);
    pollStatus();
    return () => clearInterval(interval);
  }, [jobId, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="card p-8 text-center">
          <div className="text-4xl mb-4">❌</div>
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--foreground)' }}>Processing Failed</h2>
          <p className="mb-6" style={{ color: 'var(--muted-foreground)' }}>{error}</p>
          <button className="btn-primary" onClick={() => router.push('/')}>Go Back</button>
        </div>
      </div>
    );
  }

  if (status?.status === 'completed') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="card p-8 text-center">
          <div className="text-4xl mb-4">✅</div>
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--foreground)' }}>Profile Ready!</h2>
          <p className="mb-6" style={{ color: 'var(--muted-foreground)' }}>Redirecting...</p>
        </div>
      </div>
    );
  }

  const currentPhaseIndex = Object.keys(PHASES).indexOf(status?.current_phase || 'upload');

  return (
    <main className="min-h-screen flex items-center justify-center" style={{ background: 'var(--background)' }}>
      <div className="container mx-auto px-4 max-w-2xl">
        <div className="card p-8">
          <div className="text-center mb-8">
            <div className="animate-spin w-12 h-12 mx-auto mb-4" style={{ color: 'var(--primary)' }}>
              <svg className="w-full h-full" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: 'var(--foreground)' }}>Processing Your Documents</h2>
            <p style={{ color: 'var(--muted-foreground)' }}>This may take 2-3 minutes</p>
          </div>

          <div className="mb-8">
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>Progress</span>
              <span className="text-sm" style={{ color: 'var(--muted-foreground)' }}>{Math.round(status?.progress || 0)}%</span>
            </div>
            <div className="progress-bar"><div className="progress-bar-fill" style={{ width: `${status?.progress || 0}%` }} /></div>
          </div>

          <div className="space-y-3">
            {Object.entries(PHASES).map(([key, { label, icon }], index) => {
              const isCompleted = index < currentPhaseIndex;
              const isCurrent = index === currentPhaseIndex;
              return (
                <div key={key} className={`flex items-center gap-3 p-3 rounded-lg ${isCurrent ? 'bg-primary/10' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${isCompleted || isCurrent ? 'bg-primary text-white' : 'bg-muted text-muted-foreground'}`} style={isCompleted || isCurrent ? { background: 'var(--primary)', color: 'white' } : {}}>
                    {isCompleted ? '✓' : icon}
                  </div>
                  <span className={`text-sm font-medium ${isCurrent ? 'text-primary' : isCompleted ? 'text-foreground' : 'text-muted-foreground'}`} style={isCurrent ? { color: 'var(--primary)' } : {}}>
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </main>
  );
}
