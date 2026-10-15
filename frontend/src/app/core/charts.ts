import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

export function chartColor(token: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(token).trim();
}
