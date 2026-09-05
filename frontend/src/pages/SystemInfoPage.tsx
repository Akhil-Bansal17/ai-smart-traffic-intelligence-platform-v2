import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusIndicator } from '@/components/StatusIndicator';
import { useBackendHealth } from '@/hooks/useBackendHealth';
import { config } from '@/config/env';
import { Server, Monitor, Database, ShieldCheck, CheckCircle2, Circle } from 'lucide-react';

const phases = [
  { id: 1, name: 'Architecture + Scaffolding', status: 'completed' },
  { id: 2, name: 'Backend Foundation', status: 'completed' },
  { id: 3, name: 'Frontend Foundation', status: 'active' },
  { id: 4, name: 'Video Ingestion', status: 'pending' },
  { id: 5, name: 'YOLO Detection', status: 'pending' },
  { id: 6, name: 'Object Tracking', status: 'pending' },
  { id: 7, name: 'Vehicle Counting', status: 'pending' },
  { id: 8, name: 'Lane Analysis', status: 'pending' },
  { id: 9, name: 'Traffic Analytics', status: 'pending' },
  { id: 10, name: 'Database Integration', status: 'pending' },
  { id: 11, name: 'Analytics Dashboard', status: 'pending' },
  { id: 12, name: 'Historical Analytics', status: 'pending' },
  { id: 13, name: 'Traffic Prediction', status: 'pending' },
  { id: 14, name: 'Signal Optimization Simulation', status: 'pending' },
  { id: 15, name: 'Emergency Corridor Simulation', status: 'pending' },
  { id: 16, name: 'Security Hardening', status: 'pending' },
  { id: 17, name: 'Testing', status: 'pending' },
  { id: 18, name: 'Docker + Deployment', status: 'pending' },
  { id: 19, name: 'Documentation', status: 'pending' },
  { id: 20, name: 'Portfolio Polish', status: 'pending' },
];

export function SystemInfoPage() {
  const { status, data, error, latencyMs, isChecking, checkHealth } = useBackendHealth();

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
            <Server className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">System Diagnostics & Information</h1>
            <p className="text-xs text-slate-400 mt-1">
              Live status of frontend application, backend service, environment variables, and project roadmap.
            </p>
          </div>
        </div>
      </div>

      {/* Diagnostics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backend Status Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Server className="h-4 w-4 text-cyan-400" />
                <span>Backend Service</span>
              </CardTitle>
              <Badge variant={status === 'online' ? 'success' : status === 'offline' ? 'danger' : 'warning'} size="sm">
                {status.toUpperCase()}
              </Badge>
            </div>
            <CardDescription>FastAPI REST Service connectivity</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <StatusIndicator
              status={status}
              data={data}
              error={error}
              latencyMs={latencyMs}
              isChecking={isChecking}
              onRefresh={checkHealth}
              variant="compact"
            />

            <div className="text-xs font-mono bg-slate-950/70 p-3.5 rounded-lg border border-slate-800/70 space-y-2 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">Configured Base URL:</span>
                <span className="text-cyan-400">{config.apiBaseUrl || '(Not configured)'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Endpoint Checked:</span>
                <span className="text-slate-300">/api/v1/health</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Reported Version:</span>
                <span className="text-slate-300">{data?.version ? `v${data.version}` : '--'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Backend Environment:</span>
                <span className="text-slate-300">{data?.environment || '--'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Roundtrip Latency:</span>
                <span className="text-slate-300">{latencyMs !== null ? `${latencyMs} ms` : '--'}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Frontend Status Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Monitor className="h-4 w-4 text-cyan-400" />
                <span>Frontend Client</span>
              </CardTitle>
              <Badge variant="info" size="sm">VITE + REACT</Badge>
            </div>
            <CardDescription>Client runtime and environment</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-xs font-mono bg-slate-950/70 p-3.5 rounded-lg border border-slate-800/70 space-y-2 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">Build Mode:</span>
                <span className="text-cyan-400">{config.mode}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Development Mode:</span>
                <span className="text-slate-300">{config.isDev ? 'true' : 'false'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Framework:</span>
                <span className="text-slate-300">React 18 (TypeScript)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Styling:</span>
                <span className="text-slate-300">Tailwind CSS</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Router:</span>
                <span className="text-slate-300">React Router v6</span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-400">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span>Strict TypeScript, typed API client, zero hard-coded URLs.</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Project Roadmap Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-4 w-4 text-cyan-400" />
            <span>20-Phase Implementation Roadmap</span>
          </CardTitle>
          <CardDescription>
            Current phase progress and verified status tracking
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {phases.map((p) => {
              const isCompleted = p.status === 'completed';
              const isActive = p.status === 'active';

              return (
                <div
                  key={p.id}
                  className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                    isCompleted
                      ? 'bg-emerald-950/30 border-emerald-900/50 text-emerald-300'
                      : isActive
                      ? 'bg-cyan-950/40 border-cyan-800/60 text-cyan-300'
                      : 'bg-slate-900/40 border-slate-800/60 text-slate-400'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    {isCompleted ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                    ) : (
                      <Circle className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                    )}
                    <span className="truncate">
                      <span className="font-mono font-semibold">Ph {p.id}:</span> {p.name}
                    </span>
                  </div>
                  <span className="text-[10px] uppercase font-mono font-semibold shrink-0 ml-1.5">
                    {isCompleted ? 'DONE' : isActive ? 'NOW' : 'TODO'}
                  </span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
