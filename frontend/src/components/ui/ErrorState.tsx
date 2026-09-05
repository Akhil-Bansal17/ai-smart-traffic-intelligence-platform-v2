import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import { cn } from '@/utils/cn';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  code?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}

export function ErrorState({
  title = 'Failed to load data',
  message = 'An unexpected error occurred while communicating with the service.',
  code,
  onRetry,
  isRetrying = false,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center rounded-xl bg-rose-950/20 border border-rose-900/40 text-slate-300 gap-3 max-w-md mx-auto',
        className
      )}
    >
      <div className="p-3 rounded-full bg-rose-900/30 text-rose-400 border border-rose-800/50">
        <AlertTriangle className="h-6 w-6" />
      </div>

      <div className="space-y-1">
        <h4 className="text-sm font-semibold text-rose-200">{title}</h4>
        <p className="text-xs text-slate-400 leading-relaxed">{message}</p>
        {code && (
          <p className="text-[11px] font-mono text-rose-400/80 mt-1">
            Error code: <span className="bg-rose-950/80 px-1.5 py-0.5 rounded">{code}</span>
          </p>
        )}
      </div>

      {onRetry && (
        <Button
          size="sm"
          variant="outline"
          onClick={onRetry}
          isLoading={isRetrying}
          leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          className="mt-2 border-rose-800/60 text-rose-200 hover:bg-rose-900/30 hover:border-rose-700"
        >
          Try Again
        </Button>
      )}
    </div>
  );
}
