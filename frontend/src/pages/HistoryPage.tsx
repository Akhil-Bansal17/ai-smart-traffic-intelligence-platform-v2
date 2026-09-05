import { PlaceholderPage } from '@/components/PlaceholderPage';
import { History } from 'lucide-react';

export function HistoryPage() {
  return (
    <PlaceholderPage
      pageTitle="Historical Traffic Analytics & Reports"
      phaseNumber={12}
      phaseName="Historical Analytics & Trends"
      category="Analytics"
      description="Aggregates past video analysis sessions, hourly/daily traffic patterns, historical congestion trends, and exports structured CSV/PDF reports for municipal and civil engineering review."
      icon={<History className="h-6 w-6" />}
      plannedFeatures={[
        {
          title: 'Historical Session Browser',
          description: 'Filter and inspect completed video analysis runs by date, location, and camera.',
        },
        {
          title: 'Long-Term Congestion Trends',
          description: 'Visualize weekly and monthly peak hour patterns across multiple intersections.',
        },
        {
          title: 'Exportable Data Reports',
          description: 'Generate formatted PDF summaries and export granular CSV detection time-series.',
        },
        {
          title: 'Session Comparison Tool',
          description: 'Compare traffic flow metrics across different days or under distinct weather conditions.',
        },
      ]}
    />
  );
}
