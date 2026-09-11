import React from 'react';
import { DataProvenanceSection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ShieldCheck, FileText, CheckCircle2, AlertCircle, Link2 } from 'lucide-react';

interface DataProvenancePanelProps {
  data: DataProvenanceSection;
}

export const DataProvenancePanel: React.FC<DataProvenancePanelProps> = ({ data }) => {
  const {
    active_session_id,
    video_filename,
    source_type,
    provenance_verified,
    source_reference,
    license_reference,
    provenance_note,
    uploaded_at,
  } = data;

  const hasVideo = !!video_filename;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/50 text-emerald-400">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Data Provenance & Trust Boundary</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              Verified lineage, license references, and anti-fabrication metadata for displayed traffic data
            </p>
          </div>
        </div>

        <ProvenanceBadge provenance={data.provenance} size="sm" showCategory={true} />
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {hasVideo ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium">Video Source Classification</div>
              <div className="mt-1 flex items-center gap-1.5">
                <Badge
                  variant={source_type === 'real_world' && provenance_verified ? 'success' : 'warning'}
                  size="sm"
                >
                  {source_type === 'real_world' ? 'Real-World Video' : 'Synthetic Test Clip'}
                </Badge>
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono truncate">{video_filename}</div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium">Verification Status</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs font-semibold">
                {provenance_verified ? (
                  <span className="text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Verified Genuine
                  </span>
                ) : (
                  <span className="text-amber-400 flex items-center gap-1">
                    <AlertCircle className="h-3.5 w-3.5" />
                    Unverified / Test Clip
                  </span>
                )}
              </div>
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {provenance_verified ? 'Passed Provenance Gate' : 'Default / Test Pipeline'}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium">Source / Repository</div>
              <div className="mt-1 text-xs font-mono text-cyan-300 truncate">
                {source_reference ? (
                  <a
                    href={source_reference}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline flex items-center gap-1"
                  >
                    <Link2 className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="truncate">{source_reference.replace('https://github.com/', '')}</span>
                  </a>
                ) : (
                  'Local / Uploaded'
                )}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">
                License: <span className="text-slate-200 font-mono">{license_reference || 'Unspecified'}</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium">Session Metadata</div>
              <div className="mt-1 text-xs font-mono text-slate-200 truncate">
                {active_session_id ? `ID: ${active_session_id.substring(0, 13)}...` : 'None'}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">
                Uploaded: {uploaded_at ? new Date(uploaded_at).toLocaleDateString() : 'N/A'}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-slate-400 rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-col items-center gap-2">
            <FileText className="h-6 w-6 text-slate-400" />
            <span>No video metadata available. Upload or process a video to record provenance.</span>
          </div>
        )}

        {provenance_note && (
          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 font-mono">
            <span className="text-slate-400">Provenance Notes: </span>
            {provenance_note}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
