import { Loader2 } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface LoadingStateProps {
  message?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function LoadingState({
  message = 'Loading traffic intelligence data...',
  className,
  size = 'md',
}: LoadingStateProps) {
  const sizeMap = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center gap-3 text-slate-400',
        className
      )}
    >
      <Loader2 className={cn('animate-spin text-cyan-500', sizeMap[size])} />
      {message && <p className="text-xs font-medium text-slate-400">{message}</p>}
      <span className="sr-only">Loading</span>
    </div>
  );
}
