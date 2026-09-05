import { PlaceholderPage } from '@/components/PlaceholderPage';
import { Settings } from 'lucide-react';

export function SettingsPage() {
  return (
    <PlaceholderPage
      pageTitle="Platform Configuration & Settings"
      phaseNumber={16}
      phaseName="Security Hardening & Configuration"
      category="System"
      description="Manage runtime parameters including YOLO confidence thresholds, lane boundary polygon coordinates, counting line calibrations, density scoring weights, and data retention policies."
      icon={<Settings className="h-6 w-6" />}
      plannedFeatures={[
        {
          title: 'CV Model & Tracker Calibration',
          description: 'Configure confidence cutoffs, tracking thresholds, and frame processing rates.',
        },
        {
          title: 'Lane Polygons & Counting Line Editor',
          description: 'Interactive graphical editor to define lane boundaries and directional crossing triggers.',
        },
        {
          title: 'Congestion Scoring Weight Tuning',
          description: 'Adjust weights for velocity, occupancy, and queue length in the congestion formula.',
        },
        {
          title: 'Data Retention & Privacy Controls',
          description: 'Set automated data retention policies for high-volume per-frame detection logs.',
        },
      ]}
    />
  );
}
