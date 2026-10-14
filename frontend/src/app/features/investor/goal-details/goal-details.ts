import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { InvestorCommandsService } from '../../../core/investor/investor-commands.service';
import { InvestorQueriesService } from '../../../core/investor/investor-queries.service';
import {
  CANCELLABLE,
  CHANNELS,
  FLEXIBILITY,
  GoalDetails,
  LIQUIDITY,
  TimelineItem,
  apiErrorMessage,
  formatDate,
  goalTypeLabel,
  optionLabel,
} from '../../../core/investor/investor.models';
import { MoneyPipe } from '../../../shared/money.pipe';
import { StatusChip } from '../../../shared/status-chip';

@Component({
  selector: 'gv-goal-details',
  imports: [RouterLink, MatButtonModule, MoneyPipe, StatusChip],
  templateUrl: './goal-details.html',
  styleUrl: './goal-details.scss',
})
export class GoalDetailsPage {
  private readonly queries = inject(InvestorQueriesService);
  private readonly commands = inject(InvestorCommandsService);
  private readonly router = inject(Router);

  protected readonly goal = signal<GoalDetails | null>(null);
  protected readonly timeline = signal<TimelineItem[]>([]);
  protected readonly failed = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal('');
  protected readonly formatDate = formatDate;
  protected readonly goalTypeLabel = goalTypeLabel;
  protected readonly cancellable = CANCELLABLE;

  constructor() {
    const id = this.routeId();
    if (id) {
      this.load(id);
    } else {
      this.failed.set(true);
    }
  }

  protected load(goalId = this.routeId()): void {
    if (!goalId) {
      return;
    }
    this.failed.set(false);
    this.goal.set(null);
    this.queries.goal(goalId).subscribe({
      next: (goal) => {
        this.goal.set(goal);
        if (goal.activeRequestId) {
          this.queries.timeline(goal.activeRequestId).subscribe({
            next: (page) => this.timeline.set(page.items),
            error: () => this.timeline.set([]),
          });
        } else {
          this.timeline.set([]);
        }
      },
      error: () => {
        this.goal.set(null);
        this.failed.set(true);
      },
    });
  }

  protected flexibility(value: string): string {
    return optionLabel(FLEXIBILITY, value);
  }

  protected liquidity(value: string): string {
    return optionLabel(LIQUIDITY, value);
  }

  protected channels(values: string[]): string {
    if (!values.length) {
      return 'אין';
    }
    return values.map((value) => optionLabel(CHANNELS, value)).join(', ');
  }

  protected cancel(): void {
    const goal = this.goal();
    if (!goal?.activeRequestId || !confirm('לבטל את הבקשה?')) {
      return;
    }
    this.busy.set(true);
    this.error.set('');
    this.commands.cancelRequest(goal.activeRequestId, 'בוטל על ידי המשקיע').subscribe({
      next: () => {
        this.busy.set(false);
        this.load(goal.goalId);
      },
      error: (error: unknown) => {
        this.busy.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }

  protected archive(): void {
    const goal = this.goal();
    if (!goal || !confirm('להעביר את היעד לארכיון?')) {
      return;
    }
    this.busy.set(true);
    this.commands.archiveGoal(goal.goalId).subscribe({
      next: () => void this.router.navigateByUrl('/investor'),
      error: (error: unknown) => {
        this.busy.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }

  private routeId(): string | null {
    let route = this.router.routerState.snapshot.root;
    while (route.firstChild) {
      route = route.firstChild;
    }
    return route.paramMap.get('id');
  }
}
