import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { Subscription, switchMap, timer } from 'rxjs';
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
import { AssessmentCard } from './assessment-card';

@Component({
  selector: 'gv-goal-details',
  imports: [RouterLink, MatButtonModule, MoneyPipe, StatusChip, AssessmentCard],
  templateUrl: './goal-details.html',
  styleUrl: './goal-details.scss',
})
export class GoalDetailsPage {
  private readonly queries = inject(InvestorQueriesService);
  private readonly commands = inject(InvestorCommandsService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private poll: Subscription | null = null;

  protected readonly goal = signal<GoalDetails | null>(null);
  protected readonly timeline = signal<TimelineItem[]>([]);
  protected readonly failed = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal('');
  protected readonly refreshError = signal('');
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

  protected load(goalId = this.routeId(), silent = false): void {
    if (!goalId) {
      return;
    }
    if (!silent) {
      this.failed.set(false);
      this.goal.set(null);
    }
    this.queries.goal(goalId).subscribe({
      next: (goal) => {
        this.failed.set(false);
        this.refreshError.set('');
        this.goal.set(goal);
        this.loadTimeline(goal);
        this.arm(goal);
      },
      error: () => {
        if (silent && this.goal()) {
          this.refreshError.set('לא הצלחנו לרענן את ההערכה.');
          return;
        }
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

  private loadTimeline(goal: GoalDetails): void {
    if (!goal.activeRequestId) {
      this.timeline.set([]);
      return;
    }
    this.queries.timeline(goal.activeRequestId).subscribe({
      next: (page) => this.timeline.set(page.items),
      error: () => this.timeline.set([]),
    });
  }

  private arm(goal: GoalDetails): void {
    const live = goal.requestStatus === 'SUBMITTED' || goal.requestStatus === 'AI_PROCESSING';
    if (!live) {
      this.poll?.unsubscribe();
      this.poll = null;
      return;
    }
    if (this.poll) {
      return;
    }
    this.poll = timer(15000, 15000)
      .pipe(
        switchMap(() => this.queries.goal(goal.goalId)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (next) => {
          this.goal.set(next);
          this.refreshError.set('');
          this.loadTimeline(next);
          if (next.requestStatus !== 'SUBMITTED' && next.requestStatus !== 'AI_PROCESSING') {
            this.poll?.unsubscribe();
            this.poll = null;
          }
        },
        error: () => {
          this.refreshError.set('לא הצלחנו לרענן את ההערכה.');
          this.poll = null;
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
