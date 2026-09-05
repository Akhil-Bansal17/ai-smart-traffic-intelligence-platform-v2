import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Clock, Layers, ArrowRight, ShieldAlert } from 'lucide-react';

export interface PlannedFeature {
  title: string;
  description: string;
}

export interface PlaceholderPageProps {
  pageTitle: string;
  phaseNumber: number | string;
  phaseName: string;
  category: 'CV Pipeline' | 'Analytics' | 'Machine Learning' | 'Decision Support Simulation' | 'System';
  description: string;
  icon: React.ReactNode;
  plannedFeatures?: PlannedFeature[];
  isSimulation?: boolean;
}

export function PlaceholderPage({
  pageTitle,
  phaseNumber,
  phaseName,
  category,
  description,
  icon,
  plannedFeatures = [],
  isSimulation = false,
}: PlaceholderPageProps) {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-cyan-900/40 bg-gradient-to-r from-slate-900/90 via-slate-900/80 to-cyan-950/20 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div className="p-3.5 rounded-xl bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
            {icon}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold tracking-tight text-white">{pageTitle}</h1>
              <Badge variant="warning" size="sm">
                <Clock className="h-3 w-3 mr-1" />
                Not Yet Implemented
              </Badge>
              {isSimulation && (
                <Badge variant="simulation" size="sm">
                  SIMULATION
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Planned for <span className="text-cyan-300 font-semibold">Phase {phaseNumber}: {phaseName}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Badge variant="info" size="md">
            <Layers className="h-3 w-3 mr-1" />
            {category}
          </Badge>
        </div>
      </div>

      {/* Main Architecture & Plan Card */}
      <Card>
        <CardHeader>
          <CardTitle>Architecture & Scope</CardTitle>
          <CardDescription>
            Per ARCHITECTURE.md specifications, this module will be built in its scheduled phase.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/40 p-4 rounded-lg border border-slate-800/60">
            {description}
          </p>

          {plannedFeatures.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Planned Capabilities
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {plannedFeatures.map((feature, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg border border-slate-800/70 bg-slate-900/40 space-y-1 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-2 text-xs font-medium text-slate-200">
                      <ArrowRight className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                      <span>{feature.title}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 pl-5.5 leading-normal">
                      {feature.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {isSimulation && (
            <div className="flex items-start gap-3 p-3.5 rounded-lg bg-indigo-950/30 border border-indigo-800/40 text-indigo-300 text-xs">
              <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5 text-indigo-400" />
              <div>
                <span className="font-semibold text-indigo-200">Simulation-Only Notice: </span>
                In accordance with project integrity commitments, all optimization algorithms and emergency routing
                features in this section operate strictly as advisory simulations and do not interact with live municipal control infrastructure.
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
