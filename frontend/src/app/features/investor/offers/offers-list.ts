import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { InvestorQueriesService } from '../../../core/investor/investor-queries.service';
import { OfferView, formatDate } from '../../../core/investor/investor.models';
import { Disclaimer } from '../../../shared/disclaimer';
import { StatusChip } from '../../../shared/status-chip';

@Component({
  selector: 'gv-offers-list',
  imports: [RouterLink, MatButtonModule, Disclaimer, StatusChip],
  templateUrl: './offers-list.html',
  styleUrl: './offers-list.scss',
})
export class OffersList {
  private readonly queries = inject(InvestorQueriesService);

  protected readonly formatDate = formatDate;
  protected readonly offers = signal<OfferView[] | null>(null);
  protected readonly failed = signal(false);

  constructor() {
    this.load();
  }

  protected load(): void {
    this.failed.set(false);
    this.offers.set(null);
    this.queries.offers().subscribe({
      next: (page) => this.offers.set(page.items),
      error: () => {
        this.offers.set([]);
        this.failed.set(true);
      },
    });
  }
}
