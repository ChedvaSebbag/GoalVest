import { Component, computed, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { AgentCommandsService } from '../../../core/agent/agent-commands.service';
import { AgentQueriesService } from '../../../core/agent/agent-queries.service';
import { LeadDetails, OfferDraftItem } from '../../../core/agent/agent.models';
import { CommandResult, apiErrorMessage, formatDate, goalTypeLabel } from '../../../core/investor/investor.models';
import { AssessmentCard } from '../../investor/goal-details/assessment-card';
import { MoneyPipe } from '../../../shared/money.pipe';
import { StatusChip } from '../../../shared/status-chip';

import { InfoTip } from '../../../shared/info-tip';
import { RequestJourney } from '../../../shared/request-journey';

@Component({
  selector: 'gv-lead-details',
  imports: [FormsModule, RouterLink, MatButtonModule, AssessmentCard, MoneyPipe, StatusChip, InfoTip, RequestJourney],
  templateUrl: './lead-details.html',
  styleUrl: './lead-details.scss',
})
export class LeadDetailsPage {
  private readonly queries = inject(AgentQueriesService);
  private readonly commands = inject(AgentCommandsService);
  private readonly route = inject(ActivatedRoute);

  protected readonly formatDate = formatDate;
  protected readonly goalTypeLabel = goalTypeLabel;
  protected readonly lead = signal<LeadDetails | null>(null);
  protected readonly failed = signal(false);
  protected readonly busy = signal(false);
  protected readonly message = signal('');
  protected readonly offerItems = signal<OfferDraftItem[]>([{ productId: '', percent: null }]);
  protected note = '';
  protected reason = '';
  protected offerMessage = '';

  protected readonly offerSum = computed(() =>
    this.offerItems().reduce((sum, item) => sum + (Number(item.percent) || 0), 0),
  );

  constructor() {
    this.load();
  }

  protected load(): void {
    const requestId = this.route.snapshot.paramMap.get('id');
    if (!requestId) {
      this.failed.set(true);
      this.lead.set(null);
      return;
    }
    this.failed.set(false);
    this.queries.lead(requestId).subscribe({
      next: (lead) => this.lead.set(lead),
      error: () => {
        this.lead.set(null);
        this.failed.set(true);
      },
    });
  }

  protected claim(): void {
    this.run((id) => this.commands.claim(id));
  }

  protected approve(dialog: HTMLDialogElement): void {
    this.run((id) => this.commands.approve(id, this.note), dialog);
  }

  protected reject(dialog: HTMLDialogElement): void {
    if (!this.note.trim()) {
      this.message.set('חובה לכתוב הערה בדחייה');
      return;
    }
    this.run((id) => this.commands.reject(id, this.note), dialog);
  }

  protected reevaluate(dialog: HTMLDialogElement): void {
    if (!this.reason.trim()) {
      this.message.set('חובה לכתוב סיבה');
      return;
    }
    this.run((id) => this.commands.reevaluate(id, this.reason), dialog);
  }

  protected addOfferRow(): void {
    if (this.offerItems().length >= 3) {
      return;
    }
    this.offerItems.update((items) => [...items, { productId: '', percent: null }]);
  }

  protected removeOfferRow(index: number): void {
    this.offerItems.update((items) => items.filter((_, position) => position !== index));
  }

  protected updateOffer(index: number, patch: Partial<OfferDraftItem>): void {
    this.offerItems.update((items) => items.map((item, position) => position === index ? { ...item, ...patch } : item));
  }

  protected sendOffer(dialog: HTMLDialogElement): void {
    const items = this.offerItems();
    if (items.length < 1 || items.length > 3 || items.some((item) => !item.productId || !item.percent)) {
      this.message.set('יש לבחור בין מוצר אחד לשלושה ולהזין אחוז לכל אחד');
      return;
    }
    if (new Set(items.map((item) => item.productId)).size !== items.length) {
      this.message.set('אי אפשר לבחור את אותו מוצר פעמיים');
      return;
    }
    if (this.offerSum() !== 100) {
      this.message.set('סכום האחוזים חייב להיות 100');
      return;
    }
    if (!this.offerMessage.trim()) {
      this.message.set('חובה לכתוב הודעה');
      return;
    }
    this.run((id) => this.commands.sendOffer(
      id,
      items.map((item) => ({ productId: item.productId, percent: Number(item.percent) })),
      this.offerMessage.trim(),
    ), dialog);
  }

  private run(action: (requestId: string) => Observable<CommandResult>, dialog?: HTMLDialogElement): void {
    const requestId = this.lead()?.requestId;
    if (!requestId || this.busy()) {
      return;
    }
    this.busy.set(true);
    this.message.set('');
    action(requestId).subscribe({
      next: () => {
        this.busy.set(false);
        dialog?.close();
        this.load();
      },
      error: (error: unknown) => {
        this.busy.set(false);
        this.message.set(apiErrorMessage(error));
      },
    });
  }

  protected noActionText(status: string, claimedByMe: boolean): string {
    switch (status) {
      case 'IN_REVIEW':
        return claimedByMe ? '' : 'הליד בטיפול של סוכן אחר מהגוף שלך.';
      case 'OFFER_SENT':
        return 'ההצעה נשלחה. ממתינים לתשובת המשקיע, ותופיע התראה כשיענה.';
      case 'ACCEPTED':
        return 'המשקיע אישר את ההצעה. כדאי ליצור איתו קשר להשלמת ההצטרפות.';
      case 'REEVALUATION_REQUESTED':
        return 'הבקשה חזרה לסוכן ה-AI. הליד יחזור לרשימת החדשים כשההערכה המעודכנת תהיה מוכנה.';
      case 'CANCELLED':
        return 'המשקיע ביטל את הבקשה.';
      default:
        return 'אין פעולה זמינה בסטטוס הזה.';
    }
  }
}
