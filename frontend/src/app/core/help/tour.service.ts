import { Injectable, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { HelpRole, TOURS } from './help-content';
import { TourDialog, TourDialogData } from '../../shared/tour-dialog';

const KEY = (role: HelpRole) => `gv.tour.${role}.v1`;

/** סיור פתיחה: מוצג אוטומטית פעם אחת לכל תפקיד, ואפשר להציג אותו שוב מדף העזרה. */
@Injectable({ providedIn: 'root' })
export class TourService {
  private readonly dialog = inject(MatDialog);
  private open = false;

  maybeShow(role: string | null | undefined): void {
    if (!isHelpRole(role) || this.seen(role)) {
      return;
    }
    this.show(role);
  }

  show(role: string | null | undefined): void {
    if (!isHelpRole(role) || this.open) {
      return;
    }
    this.open = true;
    const ref = this.dialog.open<TourDialog, TourDialogData>(TourDialog, {
      data: { steps: TOURS[role] },
      width: '520px',
      maxWidth: 'calc(100vw - 32px)',
      direction: 'rtl',
      autoFocus: 'first-tabbable',
      ariaLabel: 'סיור היכרות עם המערכת',
    });
    ref.afterClosed().subscribe(() => {
      this.open = false;
      this.markSeen(role);
    });
  }

  private seen(role: HelpRole): boolean {
    try {
      return localStorage.getItem(KEY(role)) === 'done';
    } catch {
      return false;
    }
  }

  private markSeen(role: HelpRole): void {
    try {
      localStorage.setItem(KEY(role), 'done');
    } catch {
      // בלי אחסון מקומי הסיור פשוט יוצג שוב בכניסה הבאה
    }
  }
}

function isHelpRole(role: string | null | undefined): role is HelpRole {
  return role === 'INVESTOR' || role === 'AGENT';
}
