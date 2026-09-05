import { PlaceholderPage } from '@/components/PlaceholderPage';
import { TrendingUp } from 'lucide-react';

export function PredictionsPage() {
  return (
    <PlaceholderPage
      pageTitle="Short-Horizon Traffic Predictions"
      phaseNumber={13}
      phaseName="Traffic Prediction Models"
      category="Machine Learning"
      description="Executes scikit-learn / XGBoost time-series inference to forecast traffic volume, congestion probability, and expected queue lengths over a 5–15 minute short horizon, evaluated on held-out empirical data."
      icon={<TrendingUp className="h-6 w-6" />}
      plannedFeatures={[
        {
          title: '5–15 Minute Short-Horizon Forecasts',
          description: 'Anticipates queue buildup and surge congestion before gridlock manifests.',
        },
        {
          title: 'Model Confidence Bands',
          description: 'Renders prediction intervals reflecting model uncertainty across forecast horizons.',
        },
        {
          title: 'Trained Model Performance Metrics',
          description: 'Transparently displays verified MAE, RMSE, and R² scores evaluated during training.',
        },
        {
          title: 'Automated Surge Alerts',
          description: 'Early warnings when predicted density crosses high/severe congestion thresholds.',
        },
      ]}
    />
  );
}
