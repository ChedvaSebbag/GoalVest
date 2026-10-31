import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { chartColor } from '../../../core/charts';
import { InvestorQueriesService } from '../../../core/investor/investor-queries.service';
import {
  InvestorDashboard as DashboardView,
  InvestorDashboardGoal,
  formatDate,
  goalTypeLabel,
} from '../../../core/investor/investor.models';
import { Disclaimer } from '../../../shared/disclaimer';
import { MoneyPipe } from '../../../shared/money.pipe';
import { StatusChip } from '../../../shared/status-chip';

@Component({
  selector: 'gv-investor-dashboard',
  imports: [FormsModule, RouterLink, MatButtonModule, BaseChartDirective, Disclaimer, MoneyPipe, StatusChip],
  templateUrl: './investor-dashboard.html',
  styleUrl: './investor-dashboard.scss',
})
export class InvestorDashboard {
  private readonly queries = inject(InvestorQueriesService);
  private readonly router = inject(Router);

  protected readonly formatDate = formatDate;
  protected readonly goalTypeLabel = goalTypeLabel;
  protected readonly dashboard = signal<DashboardView | null>(null);
  protected readonly failed = signal(false);
  protected readonly selectedId = signal<string | null>(null);
  protected query = '';

  protected readonly selected = computed(() => {
    const goals = this.dashboard()?.goals ?? [];
    return goals.find((goal) => goal.goalId === this.selectedId()) ?? goals[0] ?? null;
  });

  protected readonly donut = computed<ChartData<'doughnut'>>(() => {
    const allocation = this.selected()?.assessment?.allocation;
    return {
      labels: ['שוק ההון', 'קרן השתלמות', 'גמל ופוליסה'],
      datasets: [{
        data: [
          allocation?.capitalMarket ?? 0,
          allocation?.hishtalmut ?? 0,
          allocation?.gemelPolicy ?? 0,
        ],
        backgroundColor: [
          chartColor('--gv-primary'),
          chartColor('--gv-accent'),
          chartColor('--gv-success'),
        ],
      }],
    };
  });

  protected readonly donutOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    plugins: { legend: { rtl: true, labels: { font: { family: 'Heebo' } } } },
  };

  constructor() {
    this.load();
  }

  protected load(): void {
    this.failed.set(false);
    this.dashboard.set(null);
    this.queries.dashboard().subscribe({
      next: (dashboard) => {
        this.dashboard.set(dashboard);
        this.selectedId.set(dashboard.goals[0]?.goalId ?? null);
      },
      error: () => {
        this.dashboard.set({ plannedCapital: '0.00', activeGoals: 0, pendingOffers: 0, goals: [] });
        this.failed.set(true);
      },
    });
  }

  protected choose(goal: InvestorDashboardGoal): void {
    this.selectedId.set(goal.goalId);
  }

  protected search(): void {
    void this.router.navigate(['/products'], { queryParams: { q: this.query.trim() } });
  }

  protected statusOf(goal: InvestorDashboardGoal): string {
    return goal.requestStatus ?? 'NO_REQUEST';
  }
}
