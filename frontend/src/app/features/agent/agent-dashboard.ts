import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { catchError, forkJoin, of, Subject, startWith, switchMap, timer } from 'rxjs';
import { AgentQueriesService } from '../../core/agent/agent-queries.service';
import { AgentDashboard as AgentKpis, LeadSummary, ProductInterest } from '../../core/agent/agent.models';
import { chartColor } from '../../core/charts';
import { GOAL_TYPES, formatDate, goalTypeLabel } from '../../core/investor/investor.models';
import { MoneyPipe } from '../../shared/money.pipe';
import { StatusChip } from '../../shared/status-chip';

const SEEN_KEY = 'gv-agent-seen';

@Component({
  selector: 'gv-agent-dashboard',
  imports: [FormsModule, RouterLink, MatButtonModule, BaseChartDirective, MoneyPipe, StatusChip],
  templateUrl: './agent-dashboard.html',
  styleUrl: './agent-dashboard.scss',
})
export class AgentDashboard {
  private readonly queries = inject(AgentQueriesService);
  private readonly reload = new Subject<void>();

  protected readonly formatDate = formatDate;
  protected readonly goalTypeLabel = goalTypeLabel;
  protected readonly goalTypes = GOAL_TYPES;
  protected readonly tabs = [
    { id: '', label: 'הכל' },
    { id: 'AI_EVALUATED', label: 'חדשים' },
    { id: 'IN_REVIEW', label: 'בטיפול' },
    { id: 'OFFER_SENT', label: 'הצעות' },
    { id: 'ACCEPTED', label: 'התקבלו' },
    { id: 'REEVALUATION_REQUESTED', label: 'הערכה מחדש' },
  ];

  protected readonly dashboard = signal<AgentKpis | null>(null);
  protected readonly interest = signal<ProductInterest[] | null>(null);
  protected readonly leads = signal<LeadSummary[] | null>(null);
  protected readonly total = signal(0);
  protected readonly failed = signal(false);
  protected readonly status = signal('');
  protected readonly page = signal(1);
  protected minScore = '';
  protected goalType = '';
  private readonly since = localStorage.getItem(SEEN_KEY);

  protected readonly bars = computed<ChartData<'bar'>>(() => {
    const items = this.interest() ?? [];
    return {
      labels: items.map((item) => item.name),
      datasets: [
        { label: 'הומלץ', data: items.map((item) => item.recommended), backgroundColor: chartColor('--gv-primary'), stack: 'interest' },
        { label: 'הצעות', data: items.map((item) => item.offers), backgroundColor: chartColor('--gv-accent'), stack: 'interest' },
        { label: 'התקבלו', data: items.map((item) => item.accepted), backgroundColor: chartColor('--gv-success'), stack: 'interest' },
      ],
    };
  });

  protected readonly barOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { stacked: true, ticks: { font: { family: 'Heebo' } } },
      y: { stacked: true, beginAtZero: true, ticks: { precision: 0, font: { family: 'Heebo' } } },
    },
    plugins: { legend: { rtl: true, labels: { font: { family: 'Heebo' } } } },
  };

  constructor() {
    localStorage.setItem(SEEN_KEY, new Date().toISOString());
    this.reload.pipe(
      startWith(undefined),
      switchMap(() => timer(0, 15000).pipe(
        switchMap(() => this.fetch().pipe(catchError(() => of(null)))),
      )),
      takeUntilDestroyed(),
    ).subscribe((result) => {
      if (result === null) {
        this.failed.set(true);
        if (this.leads() === null) {
          this.dashboard.set({
            evaluated: 0, inReview: 0, offerSent: 0, offersSent: 0, offersAccepted: 0,
            conversionRate: null, averageScore: null,
          });
          this.interest.set([]);
          this.leads.set([]);
        }
        return;
      }
      this.dashboard.set(result.dashboard);
      this.interest.set(result.interest.items);
      this.leads.set(result.leads.items);
      this.total.set(result.leads.total);
      this.failed.set(false);
    });
  }

  protected refresh(): void {
    this.failed.set(false);
    this.page.set(1);
    this.reload.next();
  }

  protected selectTab(id: string): void {
    this.status.set(id);
    this.refresh();
  }

  protected nextPage(): void {
    this.page.update((value) => value + 1);
    this.reload.next();
  }

  protected previousPage(): void {
    this.page.update((value) => Math.max(1, value - 1));
    this.reload.next();
  }

  private fetch() {
    return forkJoin({
      dashboard: this.queries.dashboard(),
      interest: this.queries.interest(),
      leads: this.queries.leads({
        status: this.status(),
        minScore: this.minScore,
        goalType: this.goalType,
        page: this.page(),
        since: this.since,
      }),
    });
  }
}
