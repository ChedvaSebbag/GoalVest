import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { catchError, of, switchMap, timer } from 'rxjs';
import { NotificationCommandsService } from '../core/notifications/notification-commands.service';
import { AppNotification } from '../core/notifications/notification.models';
import { NotificationQueriesService } from '../core/notifications/notification-queries.service';
import { formatDate } from '../core/investor/investor.models';

@Component({
  selector: 'gv-notification-bell',
  templateUrl: './notification-bell.html',
  styleUrl: './notification-bell.scss',
})
export class NotificationBell {
  private readonly queries = inject(NotificationQueriesService);
  private readonly commands = inject(NotificationCommandsService);
  private readonly router = inject(Router);

  protected readonly formatDate = formatDate;
  protected readonly count = signal(0);
  protected readonly open = signal(false);
  protected readonly items = signal<AppNotification[] | null>(null);
  protected readonly failed = signal(false);

  constructor() {
    timer(0, 15000).pipe(
      switchMap(() => this.queries.unreadCount().pipe(catchError(() => of(null)))),
      takeUntilDestroyed(),
    ).subscribe((result) => {
      if (result) {
        this.count.set(result.count);
      }
    });
  }

  protected toggle(): void {
    const next = !this.open();
    this.open.set(next);
    if (next) {
      this.load();
    }
  }

  protected load(): void {
    this.failed.set(false);
    this.items.set(null);
    this.queries.list().subscribe({
      next: (page) => this.items.set(page.items),
      error: () => {
        this.items.set([]);
        this.failed.set(true);
      },
    });
  }

  protected openItem(item: AppNotification): void {
    const go = () => {
      this.open.set(false);
      void this.router.navigateByUrl(item.link);
    };
    if (item.isRead) {
      go();
      return;
    }
    this.commands.markRead(item.id).subscribe({
      next: () => {
        this.count.update((value) => Math.max(0, value - 1));
        go();
      },
      error: () => go(),
    });
  }
}
