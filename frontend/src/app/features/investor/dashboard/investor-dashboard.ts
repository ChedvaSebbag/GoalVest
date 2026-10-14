import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { InvestorQueriesService } from '../../../core/investor/investor-queries.service';
import { GoalSummary, formatDate, goalTypeLabel } from '../../../core/investor/investor.models';
import { MoneyPipe } from '../../../shared/money.pipe';
import { StatusChip } from '../../../shared/status-chip';

@Component({
  selector: 'gv-investor-dashboard',
  imports: [RouterLink, MatButtonModule, MoneyPipe, StatusChip],
  templateUrl: './investor-dashboard.html',
  styleUrl: './investor-dashboard.scss',
})
export class InvestorDashboard {
  private readonly queries = inject(InvestorQueriesService);

  protected readonly goals = signal<GoalSummary[] | null>(null);
  protected readonly failed = signal(false);
  protected readonly formatDate = formatDate;
  protected readonly goalTypeLabel = goalTypeLabel;

  constructor() {
    this.load();
  }

  protected load(): void {
    this.failed.set(false);
    this.goals.set(null);
    this.queries.goals().subscribe({
      next: (page) => this.goals.set(page.items),
      error: () => {
        this.goals.set([]);
        this.failed.set(true);
      },
    });
  }

  protected statusOf(goal: GoalSummary): string {
    return goal.requestStatus ?? 'NO_REQUEST';
  }
}
