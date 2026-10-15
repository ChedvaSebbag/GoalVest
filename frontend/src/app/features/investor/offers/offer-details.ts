import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { InvestorCommandsService } from '../../../core/investor/investor-commands.service';
import { InvestorQueriesService } from '../../../core/investor/investor-queries.service';
import { OfferView, apiErrorMessage, formatDate } from '../../../core/investor/investor.models';
import { Disclaimer } from '../../../shared/disclaimer';
import { StatusChip } from '../../../shared/status-chip';

@Component({
  selector: 'gv-offer-details',
  imports: [FormsModule, RouterLink, MatButtonModule, Disclaimer, StatusChip],
  templateUrl: './offer-details.html',
  styleUrl: './offer-details.scss',
})
export class OfferDetailsPage {
  private readonly queries = inject(InvestorQueriesService);
  private readonly commands = inject(InvestorCommandsService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly formatDate = formatDate;
  protected readonly offer = signal<OfferView | null>(null);
  protected readonly failed = signal(false);
  protected readonly busy = signal(false);
  protected readonly message = signal('');
  protected reason = '';

  constructor() {
    this.load();
  }

  protected load(): void {
    const offerId = this.route.snapshot.paramMap.get('id');
    if (!offerId) {
      this.failed.set(true);
      return;
    }
    this.failed.set(false);
    this.offer.set(null);
    this.queries.offer(offerId).subscribe({
      next: (offer) => this.offer.set(offer),
      error: () => {
        this.offer.set(null);
        this.failed.set(true);
      },
    });
  }

  protected accept(): void {
    const offerId = this.offer()?.offerId;
    if (!offerId) {
      return;
    }
    this.busy.set(true);
    this.message.set('');
    this.commands.acceptOffer(offerId).subscribe({
      next: () => {
        this.busy.set(false);
        this.load();
      },
      error: (error: unknown) => {
        this.busy.set(false);
        this.message.set(apiErrorMessage(error));
      },
    });
  }

  protected decline(dialog: HTMLDialogElement): void {
    const offerId = this.offer()?.offerId;
    if (!offerId) {
      return;
    }
    this.busy.set(true);
    this.message.set('');
    this.commands.declineOffer(offerId, this.reason.trim()).subscribe({
      next: () => {
        this.busy.set(false);
        dialog.close();
        void this.router.navigate(['/investor/offers']);
      },
      error: (error: unknown) => {
        this.busy.set(false);
        this.message.set(apiErrorMessage(error));
      },
    });
  }
}
