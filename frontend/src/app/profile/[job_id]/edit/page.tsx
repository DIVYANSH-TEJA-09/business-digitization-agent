"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getProfile, updateProfile } from '@/lib/api';
import type { BusinessProfile } from '@/lib/api';

export default function EditProfilePage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.job_id as string;
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [formData, setFormData] = useState({ name: '', description: '', category: '', phone: '', email: '', website: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getProfile(jobId).then((data) => {
      setProfile(data);
      setFormData({
        name: data.business_info.name || '',
        description: data.business_info.description || '',
        category: data.business_info.category || '',
        phone: data.business_info.contact?.phone || '',
        email: data.business_info.contact?.email || '',
        website: data.business_info.contact?.website || '',
      });
    }).catch(() => router.push('/'));
  }, [jobId, router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSave = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      const updated: BusinessProfile = { ...profile, business_info: { ...profile.business_info, ...formData, contact: { ...profile.business_info.contact, phone: formData.phone, email: formData.email, website: formData.website } } };
      await updateProfile(jobId, updated);
      alert('Saved!');
      router.push(`/profile/${jobId}`);
    } catch { alert('Failed to save'); }
    setSaving(false);
  };

  if (!profile) return <div className="min-h-screen flex items-center justify-center"><p style={{ color: 'var(--muted-foreground)' }}>Loading...</p></div>;

  return (
    <main className="min-h-screen" style={{ background: 'var(--background)' }}>
      <div className="sticky top-0 z-50 bg-background/80 backdrop-blur border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold" style={{ color: 'var(--foreground)' }}>Edit Profile</h1>
          <div className="flex gap-2">
            <button className="btn-secondary text-sm py-2" onClick={() => router.push(`/profile/${jobId}`)}>✕ Cancel</button>
            <button className="btn-primary text-sm py-2" onClick={handleSave} disabled={saving}>💾 {saving ? 'Saving...' : 'Save'}</button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-3xl">
        <div className="card p-8">
          <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--foreground)' }}>Business Information</h2>
          <div className="space-y-6">
            <div><label className="block text-sm font-medium mb-2" style={{ color: 'var(--foreground)' }}>Business Name *</label><input type="text" name="name" value={formData.name} onChange={handleChange} /></div>
            <div><label className="block text-sm font-medium mb-2" style={{ color: 'var(--foreground)' }}>Category</label><input type="text" name="category" value={formData.category} onChange={handleChange} /></div>
            <div><label className="block text-sm font-medium mb-2" style={{ color: 'var(--foreground)' }}>Description</label><textarea name="description" value={formData.description} onChange={handleChange} rows={4} /></div>
            <div className="grid md:grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium mb-2" style={{ color: 'var(--foreground)' }}>Phone</label><input type="text" name="phone" value={formData.phone} onChange={handleChange} /></div>
              <div><label className="block text-sm font-medium mb-2" style={{ color: 'var(--foreground)' }}>Email</label><input type="email" name="email" value={formData.email} onChange={handleChange} /></div>
            </div>
            <div><label className="block text-sm font-medium mb-2" style={{ color: 'var(--foreground)' }}>Website</label><input type="url" name="website" value={formData.website} onChange={handleChange} /></div>
          </div>
        </div>
        <div className="card p-8 mt-6"><h3 className="text-xl font-bold mb-4" style={{ color: 'var(--foreground)' }}>Services/Products</h3><p style={{ color: 'var(--muted-foreground)' }}>Edit services via JSON export/import. Full editing coming soon!</p></div>
      </div>
    </main>
  );
}
