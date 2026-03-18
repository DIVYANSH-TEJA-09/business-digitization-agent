"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getProfile, deleteProfile, exportProfile } from '@/lib/api';
import type { BusinessProfile, InventoryItem } from '@/lib/api';

// ─────────────────────────────────────────────────────────────────────────────
// Utility helpers — generic, domain-agnostic rendering
// ─────────────────────────────────────────────────────────────────────────────

/** Keys that are structural / meta and should not be rendered as data fields */
const META_KEYS = new Set([
  'service_id', 'product_id', 'name', 'description', 'category',
  'pricing', 'tags', 'image', 'id',
]);

/** Keys that contain arrays of strings (bullet-list rendering) */
function isStringArray(val: unknown): val is string[] {
  return Array.isArray(val) && val.length > 0 && val.every(v => typeof v === 'string');
}

/** Keys that contain arrays of objects (timeline / table rendering) */
function isObjectArray(val: unknown): val is Record<string, any>[] {
  return Array.isArray(val) && val.length > 0 && typeof val[0] === 'object' && val[0] !== null;
}

/** Keys that are flat key-value objects (detail card rendering) */
function isKVObject(val: unknown): val is Record<string, any> {
  return typeof val === 'object' && val !== null && !Array.isArray(val);
}

/** Turn snake_case / camelCase key into a readable label */
function humanize(key: string): string {
  return key
    .replace(/[_-]/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Flatten an item: if data lives inside a `details` sub-object, merge it up
 * so the renderer finds everything at one level. Applies generically — not
 * limited to any specific field names.
 */
function flattenItem(item: InventoryItem): InventoryItem {
  const result = { ...item };
  const details = result.details;

  if (isKVObject(details)) {
    for (const [key, val] of Object.entries(details)) {
      // Only pull up if the top-level value is empty / missing
      const topVal = result[key];
      const topEmpty =
        topVal === undefined ||
        topVal === null ||
        topVal === '' ||
        (Array.isArray(topVal) && topVal.length === 0) ||
        (isKVObject(topVal) && Object.keys(topVal).length === 0);

      if (topEmpty && val !== undefined && val !== null && val !== '') {
        result[key] = val;
      }
    }
  }

  return result;
}

// ─────────────────────────────────────────────────────────────────────────────
// Generic sub-components
// ─────────────────────────────────────────────────────────────────────────────

/** Render a flat Record<string, primitive> as small info cards */
function KeyValueCards({ data, exclude }: { data: Record<string, any>; exclude?: Set<string> }) {
  const entries = Object.entries(data).filter(
    ([k, v]) => v !== null && v !== undefined && v !== '' && !(exclude ?? META_KEYS).has(k) && typeof v !== 'object'
  );
  if (entries.length === 0) return null;
  return (
    <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
      {entries.map(([k, v]) => (
        <div key={k} className="card p-3">
          <span className="text-xs block mb-1" style={{ color: 'var(--muted-foreground)' }}>{humanize(k)}</span>
          <p className="font-medium text-sm" style={{ color: 'var(--foreground)' }}>{String(v)}</p>
        </div>
      ))}
    </div>
  );
}

/** Render a list of strings as a styled bullet list */
function StringList({ items, icon }: { items: string[]; icon?: string }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm" style={{ color: 'var(--muted-foreground)' }}>
          <span className="mt-0.5 flex-shrink-0">{icon ?? '•'}</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Render an array of objects as a timeline / step list */
function StepTimeline({ steps }: { steps: Record<string, any>[] }) {
  // Try to find "label" and "body" keys heuristically
  const labelKey = findKey(steps[0], ['day', 'step', 'phase', 'stage', 'title', 'name', 'label', 'number']);
  const bodyKey = findKey(steps[0], ['activity', 'description', 'content', 'text', 'details', 'summary', 'title']);
  const allKeys = Object.keys(steps[0]);

  return (
    <div className="space-y-3">
      {steps.map((step, i) => {
        const label = labelKey ? String(step[labelKey]) : String(i + 1);
        const body = bodyKey ? String(step[bodyKey]) : null;
        const extraKeys = allKeys.filter(k => k !== labelKey && k !== bodyKey && step[k] !== null && step[k] !== undefined && step[k] !== '');

        return (
          <div key={i} className="card p-4 flex gap-3" style={{ borderLeft: '4px solid var(--primary)' }}>
            <span className="w-9 h-9 rounded-full flex items-center justify-center font-bold flex-shrink-0 text-xs"
              style={{ background: 'var(--primary)', color: 'white' }}>
              {label.length <= 3 ? label : i + 1}
            </span>
            <div className="flex-1 min-w-0">
              {label.length > 3 && (
                <p className="font-semibold text-sm mb-1" style={{ color: 'var(--foreground)' }}>{label}</p>
              )}
              {body && (
                <p className="text-sm leading-relaxed" style={{ color: 'var(--muted-foreground)' }}>{body}</p>
              )}
              {extraKeys.length > 0 && (
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
                  {extraKeys.map(k => {
                    const v = step[k];
                    if (Array.isArray(v)) {
                      return <span key={k} className="text-xs" style={{ color: 'var(--muted-foreground)' }}><strong>{humanize(k)}:</strong> {v.join(', ')}</span>;
                    }
                    return <span key={k} className="text-xs" style={{ color: 'var(--muted-foreground)' }}><strong>{humanize(k)}:</strong> {String(v)}</span>;
                  })}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Find the first matching key from a priority list */
function findKey(obj: Record<string, any>, priorities: string[]): string | undefined {
  for (const p of priorities) {
    if (p in obj) return p;
  }
  return undefined;
}

/** Render Q&A style items (FAQs, etc.) */
function QAList({ items }: { items: Record<string, any>[] }) {
  const qKey = findKey(items[0], ['question', 'q', 'title', 'name']);
  const aKey = findKey(items[0], ['answer', 'a', 'response', 'content', 'description']);
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i} className="card p-4">
          <p className="font-semibold text-sm mb-1" style={{ color: 'var(--foreground)' }}>
            Q: {qKey ? String(item[qKey]) : JSON.stringify(item)}
          </p>
          {aKey && item[aKey] && (
            <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>A: {String(item[aKey])}</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Dynamic Tab system — tabs are generated from the data, not hardcoded
// ─────────────────────────────────────────────────────────────────────────────

interface TabSection {
  id: string;
  label: string;
  icon: string;
  content: React.ReactNode;
}

function buildTabs(item: InventoryItem): TabSection[] {
  const tabs: TabSection[] = [];

  // ── Tab 1: Overview (always present) ──
  const detailEntries: Record<string, any> = {};
  for (const [k, v] of Object.entries(item)) {
    if (META_KEYS.has(k)) continue;
    if (typeof v === 'string' && v || typeof v === 'number') {
      detailEntries[k] = v;
    }
  }
  // Also gather nested KV from `details` if it's a flat object
  if (isKVObject(item.details)) {
    for (const [k, v] of Object.entries(item.details)) {
      if (typeof v === 'string' && v || typeof v === 'number') {
        if (!detailEntries[k]) detailEntries[k] = v;
      }
    }
  }

  tabs.push({
    id: 'overview',
    label: 'Overview',
    icon: '📋',
    content: (
      <div className="space-y-5">
        {item.description && (
          <div>
            <h4 className="font-bold mb-2 text-sm" style={{ color: 'var(--foreground)' }}>Description</h4>
            <p className="text-sm leading-relaxed" style={{ color: 'var(--muted-foreground)' }}>{item.description}</p>
          </div>
        )}
        {Object.keys(detailEntries).length > 0 && (
          <div>
            <h4 className="font-bold mb-3 text-sm" style={{ color: 'var(--foreground)' }}>Details</h4>
            <KeyValueCards data={detailEntries} exclude={new Set(['description'])} />
          </div>
        )}
        {item.tags && isStringArray(item.tags) && (
          <div>
            <h4 className="font-bold mb-2 text-sm" style={{ color: 'var(--foreground)' }}>Tags</h4>
            <div className="flex flex-wrap gap-2">{item.tags.map((t: string, i: number) => <span key={i} className="badge">{t}</span>)}</div>
          </div>
        )}
      </div>
    ),
  });

  // ── Tab 2: Steps / Timeline (itinerary, process, stages, etc.) ──
  // Detect any array-of-objects field that looks like sequential steps
  for (const [key, val] of Object.entries(item)) {
    if (META_KEYS.has(key)) continue;
    if (key === 'faqs' || key === 'faq') continue; // separate tab
    if (isObjectArray(val)) {
      tabs.push({
        id: key,
        label: humanize(key),
        icon: '📅',
        content: <StepTimeline steps={val} />,
      });
    }
  }

  // ── Tab 3: Inclusions / Exclusions / Features (string lists) ──
  const listSections: { key: string; items: string[]; icon: string }[] = [];
  for (const [key, val] of Object.entries(item)) {
    if (META_KEYS.has(key)) continue;
    if (isStringArray(val)) {
      const icon = key.toLowerCase().includes('exclu') ? '✗' :
                   key.toLowerCase().includes('inclu') ? '✓' :
                   key.toLowerCase().includes('feature') ? '★' :
                   key.toLowerCase().includes('carry') ? '🎒' : '•';
      listSections.push({ key, items: val, icon });
    }
  }
  if (listSections.length > 0) {
    tabs.push({
      id: 'lists',
      label: listSections.length === 1 ? humanize(listSections[0].key) : 'Details',
      icon: '✅',
      content: (
        <div className="space-y-6">
          {listSections.map(({ key, items, icon }) => (
            <div key={key}>
              <h4 className="font-bold mb-3 text-sm" style={{ color: 'var(--foreground)' }}>{humanize(key)}</h4>
              <StringList items={items} icon={icon} />
            </div>
          ))}
        </div>
      ),
    });
  }

  // ── Tab 4: Policies (string fields that are policy-like) ──
  const policyEntries: { key: string; text: string }[] = [];
  for (const [key, val] of Object.entries(item)) {
    if (typeof val !== 'string' || !val) continue;
    if (key.includes('policy') || key.includes('warranty') || key.includes('refund') || key.includes('terms')) {
      policyEntries.push({ key, text: val });
    }
  }
  if (policyEntries.length > 0) {
    tabs.push({
      id: 'policies',
      label: 'Policies',
      icon: '📜',
      content: (
        <div className="space-y-5">
          {policyEntries.map(({ key, text }) => (
            <div key={key}>
              <h4 className="font-bold mb-2 text-sm" style={{ color: 'var(--foreground)' }}>{humanize(key)}</h4>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--muted-foreground)' }}>{text}</p>
            </div>
          ))}
        </div>
      ),
    });
  }

  // ── Tab 5: Nested objects (travel_info, specifications, inventory, etc.) ──
  for (const [key, val] of Object.entries(item)) {
    if (META_KEYS.has(key) || key === 'details' || key === 'pricing') continue;
    if (isKVObject(val) && Object.values(val).some(v => v !== null && v !== undefined && v !== '')) {
      tabs.push({
        id: key,
        label: humanize(key),
        icon: '📊',
        content: (
          <div>
            <KeyValueCards data={val} exclude={new Set()} />
            {/* Also render any nested string arrays */}
            {Object.entries(val).filter(([, v]) => isStringArray(v)).map(([sk, sv]) => (
              <div key={sk} className="mt-4">
                <h4 className="font-bold mb-2 text-sm" style={{ color: 'var(--foreground)' }}>{humanize(sk)}</h4>
                <StringList items={sv as string[]} />
              </div>
            ))}
          </div>
        ),
      });
    }
  }

  // ── Tab 6: FAQs ──
  const faqs = item.faqs || item.faq;
  if (isObjectArray(faqs)) {
    tabs.push({
      id: 'faqs',
      label: 'FAQ',
      icon: '❓',
      content: <QAList items={faqs} />,
    });
  }

  return tabs;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Page Component
// ─────────────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.job_id as string;
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [activeTabId, setActiveTabId] = useState('overview');

  useEffect(() => {
    getProfile(jobId).then((data) => {
      setProfile(data);
      // Merge products + services into one unified item list
      const allItems: InventoryItem[] = [
        ...(data.services ?? []).map(flattenItem),
        ...(data.products ?? []).map(flattenItem),
      ];
      setItems(allItems);
      setSelectedIdx(0);
      setActiveTabId('overview');
    }).catch(() => {}).finally(() => setLoading(false));
  }, [jobId]);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><p style={{ color: 'var(--muted-foreground)' }}>Loading...</p></div>;
  if (!profile) return <div className="min-h-screen flex items-center justify-center"><p style={{ color: 'var(--muted-foreground)' }}>Profile not found</p></div>;

  const { business_info, business_type } = profile;
  const selectedItem = items[selectedIdx] ?? null;
  const tabs = selectedItem ? buildTabs(selectedItem) : [];
  const activeTab = tabs.find(t => t.id === activeTabId) ?? tabs[0];

  // Determine item name/id key generically
  const getItemName = (item: InventoryItem) => item.name || item.title || item.product_name || item.service_name || `Item ${items.indexOf(item) + 1}`;
  const getItemId = (item: InventoryItem) => item.service_id || item.product_id || item.id || String(items.indexOf(item));
  const getItemPrice = (item: InventoryItem) => {
    const p = item.pricing;
    if (!p) return null;
    if (typeof p === 'object' && p.base_price) {
      return `${p.currency ?? '₹'}${Number(p.base_price).toLocaleString()}`;
    }
    return null;
  };

  /** Count how many data-bearing fields an item has */
  const getItemBadges = (item: InventoryItem) => {
    const badges: { label: string; color: string }[] = [];
    for (const [key, val] of Object.entries(item)) {
      if (META_KEYS.has(key)) continue;
      if (isObjectArray(val) && key !== 'faqs') badges.push({ label: `${humanize(key)} (${val.length})`, color: 'var(--primary)' });
      else if (isStringArray(val) && val.length > 0) badges.push({ label: `${humanize(key)} (${val.length})`, color: key.includes('exclu') ? '#ef4444' : '#22c55e' });
      else if (isObjectArray(val) && key === 'faqs') badges.push({ label: `FAQ (${val.length})`, color: '#8b5cf6' });
    }
    return badges;
  };

  return (
    <main className="min-h-screen" style={{ background: 'var(--background)' }}>
      {/* ── Header ── */}
      <div className="sticky top-0 z-50 bg-background/80 backdrop-blur border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold" style={{ color: 'var(--foreground)' }}>{business_info.name || 'Business Profile'}</h1>
          <div className="flex gap-2">
            <button className="btn-secondary text-sm py-2" onClick={() => exportProfile(jobId)}>📥 Export</button>
            <button className="btn-secondary text-sm py-2" onClick={() => router.push(`/profile/${jobId}/edit`)}>✏️ Edit</button>
            <button className="btn-secondary text-sm py-2" onClick={async () => { if(confirm('Delete?')) { await deleteProfile(jobId); router.push('/'); } }}>🗑️</button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* ── Hero ── */}
        <section className="card overflow-hidden mb-8">
          <div className="relative h-48 md:h-72" style={{ background: 'linear-gradient(135deg, var(--primary), var(--secondary))' }}>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-white px-4">
                <h2 className="text-3xl md:text-5xl font-bold mb-3">{business_info.name || 'Untitled Business'}</h2>
                {business_info.category && <span className="inline-block px-4 py-1.5 bg-white/20 rounded-full text-sm">{business_info.category}</span>}
              </div>
            </div>
          </div>
          <div className="p-6 md:p-8">
            {business_info.description && <p className="text-base mb-5" style={{ color: 'var(--muted-foreground)' }}>{business_info.description}</p>}
            {/* Contact — render whatever contact fields exist */}
            {business_info.contact && isKVObject(business_info.contact) && (
              <div className="flex flex-wrap gap-x-6 gap-y-2 mb-4">
                {Object.entries(business_info.contact).filter(([, v]) => typeof v === 'string' && v).map(([k, v]) => (
                  <span key={k} className="text-sm flex items-center gap-1.5" style={{ color: 'var(--muted-foreground)' }}>
                    {k.includes('phone') ? '📞' : k.includes('email') ? '✉️' : k.includes('website') || k.includes('url') ? '🌐' : '📌'}
                    {k.includes('website') || k.includes('url')
                      ? <a href={String(v)} target="_blank" rel="noopener noreferrer" className="hover:underline">{String(v).replace(/^https?:\/\//, '')}</a>
                      : String(v)}
                  </span>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <span className="badge">Type: {business_type}</span>
              {profile.validation && <span className="badge" style={{ background: 'var(--secondary)' }}>Completeness: {Math.round(profile.validation.completeness_score * 100)}%</span>}
              {items.length > 0 && <span className="badge">{items.length} {business_type === 'product' ? 'Products' : business_type === 'service' ? 'Services' : 'Items'}</span>}
            </div>
          </div>
        </section>

        {/* ── Inventory Section ── */}
        {items.length > 0 && (
          <section className="grid lg:grid-cols-3 gap-8">
            {/* ── Sidebar: Item List ── */}
            <div className="lg:col-span-1 space-y-3">
              <h3 className="text-xl font-bold mb-3" style={{ color: 'var(--foreground)' }}>
                {business_type === 'product' ? '📦 Products' : business_type === 'service' ? '💼 Services' : '📋 Inventory'}
                <span className="text-sm font-normal ml-2" style={{ color: 'var(--muted-foreground)' }}>({items.length})</span>
              </h3>
              {items.map((item, idx) => {
                const badges = getItemBadges(item);
                return (
                  <div
                    key={getItemId(item)}
                    className={`card p-4 cursor-pointer transition-all hover:shadow-md ${idx === selectedIdx ? 'ring-2 ring-primary' : ''}`}
                    onClick={() => { setSelectedIdx(idx); setActiveTabId('overview'); }}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <h4 className="font-bold text-sm" style={{ color: 'var(--foreground)' }}>{getItemName(item)}</h4>
                      {getItemPrice(item) && <span className="text-base font-bold flex-shrink-0" style={{ color: 'var(--primary)' }}>{getItemPrice(item)}</span>}
                    </div>
                    {item.description && <p className="text-xs mt-1.5 line-clamp-2" style={{ color: 'var(--muted-foreground)' }}>{item.description}</p>}
                    {item.category && <span className="text-[10px] mt-1.5 inline-block px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800" style={{ color: 'var(--muted-foreground)' }}>{item.category}</span>}
                    {badges.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {badges.map((b, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: b.color, color: 'white', opacity: 0.85 }}>{b.label}</span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* ── Main: Item Details ── */}
            <div className="lg:col-span-2">
              {selectedItem ? (
                <div className="card">
                  {/* Header */}
                  <div className="p-6 border-b" style={{ borderColor: 'var(--border)' }}>
                    <h3 className="text-2xl font-bold mb-1" style={{ color: 'var(--foreground)' }}>{getItemName(selectedItem)}</h3>
                    <div className="flex flex-wrap items-center gap-3">
                      {getItemPrice(selectedItem) && (
                        <span className="text-xl font-bold" style={{ color: 'var(--primary)' }}>
                          {getItemPrice(selectedItem)}
                          {selectedItem.pricing?.price_type && <span className="text-xs font-normal ml-1" style={{ color: 'var(--muted-foreground)' }}>/ {selectedItem.pricing.price_type}</span>}
                        </span>
                      )}
                      {selectedItem.category && <span className="badge">{selectedItem.category}</span>}
                    </div>
                  </div>

                  {/* Dynamic Tabs */}
                  {tabs.length > 1 && (
                    <div className="flex overflow-x-auto border-b" style={{ borderColor: 'var(--border)' }}>
                      {tabs.map(tab => (
                        <button
                          key={tab.id}
                          className={`px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 ${activeTabId === tab.id ? 'text-primary border-b-2 border-primary' : ''}`}
                          style={activeTabId !== tab.id ? { color: 'var(--muted-foreground)' } : undefined}
                          onClick={() => setActiveTabId(tab.id)}
                        >
                          <span>{tab.icon}</span> {tab.label}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Tab Content */}
                  <div className="p-6">
                    {activeTab?.content}
                  </div>
                </div>
              ) : (
                <div className="card p-8 text-center">
                  <p style={{ color: 'var(--muted-foreground)' }}>Select an item to view details</p>
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
