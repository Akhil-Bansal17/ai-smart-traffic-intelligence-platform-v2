import React from 'react';
import { SectionProvenanceDetail, ProvenanceState } from '@/types/dashboard';
import { CheckCircle2, Cpu, Sparkles, AlertTriangle, HelpCircle } from 'lucide-react';

interface ProvenanceBadgeProps {
  provenance: SectionProvenanceDetail;
  size?: 'sm' | 'md';
  showCategory?: boolean;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  provenance,
  size = 'md',
  showCategory = false,
}) => {
  const { state, category } = provenance;

  const getStyle = (s: ProvenanceState) => {
    switch (s) {
      case 'REAL DATA':
        return {
          container: 'bg-emerald-950/70 border-emerald-500/40 text-emerald-300 shadow-emerald-950/50',
          dot: 'bg-emerald-400',
          icon: CheckCircle2,
        };
      case 'SIMULATION':
        return {
          container: 'bg-indigo-950/70 border-indigo-500/40 text-indigo-300 shadow-indigo-950/50',
          dot: 'bg-indigo-400',
          icon: Cpu,
        };
      case 'PREDICTION':
        return {
          container: 'bg-cyan-950/70 border-cyan-500/40 text-cyan-300 shadow-cyan-950/50',
          dot: 'bg-cyan-400',
          icon: Sparkles,
        };
      case 'SYNTHETIC':
        return {
          container: 'bg-amber-950/70 border-amber-500/40 text-amber-300 shadow-amber-950/50',
          dot: 'bg-amber-400',
          icon: AlertTriangle,
        };
      case 'UNAVAILABLE':
      default:
        return {
          container: 'bg-slate-900 border-slate-700 text-slate-400 shadow-slate-950/50',
          dot: 'bg-slate-500',
          icon: HelpCircle,
        };
    }
  };

  const style = getStyle(state);
  const Icon = style.icon;

  const isSmall = size === 'sm';

  return (
    <div
      className={`inline-flex items-center gap-1.5 font-medium tracking-wide rounded-md border shadow-sm transition-all ${
        style.container
      } ${isSmall ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs'}`}
      title={provenance.description || `Data State: ${state} (${category})`}
    >
      <Icon className={isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      <span className="font-semibold">{state}</span>
      {showCategory && category && category !== 'unavailable' && (
        <span className="text-[10px] opacity-75 font-mono border-l border-current/20 pl-1.5 ml-0.5">
          {category.replace(/_/g, ' ')}
        </span>
      )}
    </div>
  );
};
