import React from 'react';
import { cn } from '@/utils/cn';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'outline' | 'simulation';
  size?: 'sm' | 'md';
}

export function Badge({
  className,
  variant = 'default',
  size = 'md',
  ...props
}: BadgeProps) {
  const variants = {
    default: 'bg-slate-800 text-slate-300 border-slate-700/60',
    success: 'bg-emerald-950/70 text-emerald-400 border-emerald-800/60',
    warning: 'bg-amber-950/70 text-amber-400 border-amber-800/60',
    danger: 'bg-rose-950/70 text-rose-400 border-rose-800/60',
    info: 'bg-cyan-950/70 text-cyan-400 border-cyan-800/60',
    outline: 'bg-transparent text-slate-400 border-slate-700',
    simulation: 'bg-indigo-950/70 text-indigo-300 border-indigo-700/60 font-mono tracking-wider',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-[10px] gap-1 font-medium',
    md: 'px-2.5 py-0.5 text-xs gap-1.5 font-medium',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border transition-colors select-none',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}
