// API configuration
const RAW_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const API_BASE_URL = RAW_URL.endsWith('/api') ? RAW_URL : `${RAW_URL}/api`;

// ─────────────────────────────────────────────────────
// Generic interfaces – the profile page renders ANY
// shape of data; no domain-specific fields are assumed.
// ─────────────────────────────────────────────────────

export interface BusinessProfile {
  profile_id: string;
  job_id: string;
  business_type: string;
  business_info: Record<string, any>;
  products?: Record<string, any>[];
  services?: Record<string, any>[];
  created_at: string;
  updated_at?: string;
  extraction_metadata?: Record<string, any>;
  validation?: {
    completeness_score: number;
    field_scores: Record<string, number>;
  };
  [key: string]: any;
}

/** A single inventory item (product or service). Fully dynamic. */
export type InventoryItem = Record<string, any>;

export interface JobStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  current_phase: string;
  error?: string;
}

export interface ProfileSummary {
  job_id: string;
  name: string;
  created_at: string;
  service_count: number;
  business_type: string;
}

// ─────────────────────────────────────────────────────
// API functions
// ─────────────────────────────────────────────────────

export async function uploadZip(file: File): Promise<{ job_id: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/status/${jobId}`);

  if (!response.ok) {
    throw new Error('Failed to get status');
  }

  return response.json();
}

export async function getProfiles(): Promise<{ profiles: ProfileSummary[] }> {
  const response = await fetch(`${API_BASE_URL}/profiles`);

  if (!response.ok) {
    throw new Error('Failed to get profiles');
  }

  return response.json();
}

export async function getProfile(jobId: string): Promise<BusinessProfile> {
  const response = await fetch(`${API_BASE_URL}/profile/${jobId}`);

  if (!response.ok) {
    throw new Error('Profile not found');
  }

  return response.json();
}

export async function updateProfile(jobId: string, profile: BusinessProfile): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE_URL}/profile/${jobId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(profile),
  });

  if (!response.ok) {
    throw new Error('Failed to update profile');
  }

  return response.json();
}

export async function deleteProfile(jobId: string): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE_URL}/profile/${jobId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Failed to delete profile');
  }

  return response.json();
}

export async function exportProfile(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/profile/${jobId}/export`);

  if (!response.ok) {
    throw new Error('Failed to export profile');
  }

  // Trigger download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `profile_${jobId}.json`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
