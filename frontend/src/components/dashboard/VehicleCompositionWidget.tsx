import React from 'react';
import { VehicleCompositionSection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { PieChart, Layers } from 'lucide-react';

interface VehicleCompositionWidgetProps {
  data: VehicleCompositionSection;
}

export const VehicleCompositionWidget: React.FC<VehicleCompositionWidgetProps> = ({ data }) => {
  const { total_counted, class_distribution } = data;

  const getClassColor = (className: string) => {
    switch (className.toLowerCase()) {
      case 'car':
        return { bar: 'bg-emerald-500', text: 'text-emerald-400', badge: 'bg-emerald-950/60 border-emerald-800/60' };
      case 'bus':
        return { bar: 'bg-cyan-500', text: 'text-cyan-400', badge: 'bg-cyan-950/60 border-cyan-800/60' };
      case 'truck':
        return { bar: 'bg-amber-500', text: 'text-amber-400', badge: 'bg-amber-950/60 border-amber-800/60' };
      case 'motorcycle':
        return { bar: 'bg-purple-500', text: 'text-purple-400', badge: 'bg-purple-950/60 border-purple-800/60' };
      case 'bicycle':
        return { bar: 'bg-pink-500', text: 'text-pink-400', badge: 'bg-pink-950/60 border-pink-800/60' };
      default:
        return { bar: 'bg-slate-500', text: 'text-slate-400', badge: 'bg-slate-900 border-slate-800' };
    }
  };

  const hasData = class_distribution && class_distribution.length > 0;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/50 text-emerald-400">
            <PieChart className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Vehicle Class Composition</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              {hasData ? `${total_counted} counted vehicles distributed across classes` : 'No counted classes'}
            </p>
          </div>
        </div>

        <ProvenanceBadge provenance={data.provenance} size="sm" />
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {hasData ? (
          <div className="space-y-2.5">
            {class_distribution.map((item) => {
              const color = getClassColor(item.class_name);
              return (
                <div key={item.class_name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold uppercase tracking-wider text-slate-300">
                      {item.class_name}
                    </span>
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-slate-200 font-bold">{item.count}</span>
                      <span className="text-slate-400 text-[11px]">({item.percentage.toFixed(1)}%)</span>
                    </div>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-950/80 border border-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${color.bar}`}
                      style={{ width: `${Math.max(item.percentage, 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-slate-400 rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-col items-center gap-2">
            <Layers className="h-6 w-6 text-slate-400" />
            <span>No vehicle counting class distributions recorded for active session.</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
