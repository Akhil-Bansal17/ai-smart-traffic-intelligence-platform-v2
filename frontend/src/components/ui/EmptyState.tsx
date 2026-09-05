import React from 'react';
import { Inbox } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title = 'No data available',
  description = 'There are currently no records or activity to display.',
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-10 text-center rounded-xl border border-slate-800/80 bg-slate-900/30 text-slate-300 gap-3 max-w-lg mx-auto',
        className
      )}
    >
      <div className="p-3.5 rounded-full bg-slate-800/80 text-slate-400 border border-slate-700/60">
        {icon || <Inbox className="h-6 w-6" />}
      </div>

      <div className="space-y-1">
        <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
        <p className="text-xs text-slate-400 max-w-sm leading-relaxed">{description}</p>
      </div>

      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
