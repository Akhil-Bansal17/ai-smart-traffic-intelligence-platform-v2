import React from 'react';
import { RecentHistorySection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { History, ArrowUpRight, Video } from 'lucide-react';
import { Link } from 'react-router-dom';

interface HistoricalSessionsWidgetProps {
  data: RecentHistorySection;
  onSelectSession?: (sessionId: string) => void;
  activeSessionId?: string | null;
}

export const HistoricalSessionsWidget: React.FC<HistoricalSessionsWidgetProps> = ({
  data,
  onSelectSession,
  activeSessionId,
}) => {
  const { total_sessions_count, sessions } = data;
  const hasSessions = sessions && sessions.length > 0;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
            <History className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Historical Video Analysis Runs</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              {hasSessions
                ? `${total_sessions_count} persisted session(s) in database — click to inspect`
                : 'No historical sessions'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge provenance={data.provenance} size="sm" />
          <Link
            to="/history"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Open Full History"
          >
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-2">
        {hasSessions ? (
          <div className="space-y-2">
            {sessions.map((s) => {
              const isActive = activeSessionId === s.id;
              return (
                <div
                  key={s.id}
                  onClick={() => onSelectSession && onSelectSession(s.id)}
                  className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                    isActive
                      ? 'bg-cyan-950/40 border-cyan-500/60 ring-1 ring-cyan-500/40 shadow-sm'
                      : 'bg-slate-950/40 border-slate-800/70 hover:border-slate-700 hover:bg-slate-950/70'
                  }`}
                >
                  <div className="min-w-0 pr-3">
                    <div className="flex items-center gap-2">
                      <Video className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                      <span className="text-xs font-semibold text-slate-200 truncate font-mono">
                        {s.original_filename}
                      </span>
                      {isActive && (
                        <Badge variant="info" size="sm" className="text-[9px] px-1 py-0">
                          Active
                        </Badge>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-2 font-mono">
                      <span>{new Date(s.started_at).toLocaleString()}</span>
                      <span>•</span>
                      <span>{s.total_vehicles_counted} vehicles</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge
                      variant={
                        s.source_type === 'real_world' && s.provenance_verified
                          ? 'success'
                          : 'warning'
                      }
                      size="sm"
                    >
                      {s.source_type === 'real_world' && s.provenance_verified
                        ? 'Real World'
                        : 'Synthetic'}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-slate-400 rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-col items-center gap-2">
            <History className="h-6 w-6 text-slate-400" />
            <span>No historical video sessions found in database.</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
