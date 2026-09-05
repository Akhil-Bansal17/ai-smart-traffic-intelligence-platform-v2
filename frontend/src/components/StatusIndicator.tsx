import { RefreshCw, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { HealthStatusState, HealthResponse } from '@/types/health';
import { ApiError } from '@/types/api';
import { cn } from '@/utils/cn';

export interface StatusIndicatorProps {
  status: HealthStatusState;
  data: HealthResponse | null;
  error: ApiError | null;
  latencyMs: number | null;
  isChecking: boolean;
  onRefresh?: () => void;
  variant?: 'compact' | 'detailed';
  className?: string;
}

export function StatusIndicator({
  status,
  data,
  error,
  latencyMs,
  isChecking,
  onRefresh,
  variant = 'compact',
  className,
}: StatusIndicatorProps) {
  const isOnline = status === 'online';
  const isOffline = status === 'offline';
  const isPending = status === 'checking';

  if (variant === 'compact') {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium transition-all select-none',
          isOnline && 'bg-emerald-950/50 border-emerald-800/60 text-emerald-300',
          isOffline && 'bg-rose-950/50 border-rose-800/60 text-rose-300',
          isPending && 'bg-amber-950/50 border-amber-800/60 text-amber-300',
          className
        )}
        title={
          isOnline
            ? `Backend Online (v${data?.version || '0.1.0'} - ${data?.environment || 'development'}${latencyMs !== null ? ` - ${latencyMs}ms` : ''})`
            : isOffline
            ? `Backend Offline: ${error?.message || 'Cannot reach API'}`
            : 'Checking backend status...'
        }
      >
        {/* Status indicator light with pulse */}
        <span className="relative flex h-2 w-2">
          {isOnline && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          )}
          <span
            className={cn(
              'relative inline-flex rounded-full h-2 w-2',
              isOnline && 'bg-emerald-500',
              isOffline && 'bg-rose-500',
              isPending && 'bg-amber-500 animate-pulse'
            )}
          />
        </span>

        <span className="font-mono text-[11px] font-semibold tracking-tight">
          {isOnline && 'API ONLINE'}
          {isOffline && 'API OFFLINE'}
          {isPending && 'CHECKING...'}
        </span>

        {isOnline && latencyMs !== null && (
          <span className="text-[10px] text-emerald-400/70 font-mono hidden sm:inline">
            {latencyMs}ms
          </span>
        )}

        {onRefresh && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRefresh();
            }}
            disabled={isChecking}
            title="Recheck backend health"
            className="text-slate-400 hover:text-white p-0.5 rounded transition-colors disabled:opacity-50 ml-0.5"
          >
            <RefreshCw className={cn('h-3 w-3', isChecking && 'animate-spin')} />
          </button>
        )}
      </div>
    );
  }

  // Detailed Card View
  return (
    <div
      className={cn(
        'p-5 rounded-xl border backdrop-blur-sm transition-all',
        isOnline && 'bg-slate-900/90 border-emerald-900/40',
        isOffline && 'bg-slate-900/90 border-rose-900/40',
        isPending && 'bg-slate-900/90 border-amber-900/40',
        className
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'p-2.5 rounded-lg border mt-0.5',
              isOnline && 'bg-emerald-950/60 border-emerald-800/60 text-emerald-400',
              isOffline && 'bg-rose-950/60 border-rose-800/60 text-rose-400',
              isPending && 'bg-amber-950/60 border-amber-800/60 text-amber-400'
            )}
          >
            {isOnline && <CheckCircle2 className="h-5 w-5" />}
            {isOffline && <XCircle className="h-5 w-5" />}
            {isPending && <AlertCircle className="h-5 w-5 animate-pulse" />}
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-slate-100">FastAPI Backend Service</h4>
              <span
                className={cn(
                  'px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold border',
                  isOnline && 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80',
                  isOffline && 'bg-rose-950/80 text-rose-300 border-rose-800/80',
                  isPending && 'bg-amber-950/80 text-amber-300 border-amber-800/80'
                )}
              >
                {status.toUpperCase()}
              </span>
            </div>

            {isOnline && data && (
              <div className="text-xs text-slate-400 space-y-0.5">
                <p>
                  Version: <span className="text-slate-200 font-mono">v{data.version}</span> •
                  Environment: <span className="text-slate-200 font-mono">{data.environment}</span>
                  {latencyMs !== null && (
                    <> • Latency: <span className="text-emerald-400 font-mono">{latencyMs}ms</span></>
                  )}
                </p>
                <p className="text-[11px] text-slate-500 font-mono">
                  Endpoint: GET /api/v1/health (HTTP 200 OK)
                </p>
              </div>
            )}

            {isOffline && (
              <div className="text-xs text-rose-300 space-y-0.5">
                <p className="font-medium">
                  {error?.code === 'network_error'
                    ? 'Backend service is offline or unreachable'
                    : error?.message || 'Service returned an error'}
                </p>
                <p className="text-[11px] text-slate-400 font-mono">
                  Check if `uvicorn app.main:app` is running on the configured port.
                </p>
              </div>
            )}

            {isPending && (
              <p className="text-xs text-slate-400">
                Pinging health endpoint at <span className="font-mono text-slate-300">/api/v1/health</span>...
              </p>
            )}
          </div>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isChecking}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', isChecking && 'animate-spin')} />
            <span>Check Now</span>
          </button>
        )}
      </div>
    </div>
  );
}
