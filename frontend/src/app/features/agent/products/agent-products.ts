import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { ProductQueriesService } from '../../../core/products/product-queries.service';
import { ProductSummary, productTypeLabel } from '../../../core/products/product.models';
import { StatusChip } from '../../../shared/status-chip';

@Component({
  selector: 'gv-agent-products',
  imports: [RouterLink, MatButtonModule, StatusChip],
  templateUrl: './agent-products.html',
  styleUrl: './agent-products.scss',
})
export class AgentProducts {
  private readonly queries = inject(ProductQueriesService);

  protected readonly items = signal<ProductSummary[] | null>(null);
  protected readonly failed = signal(false);
  protected readonly productTypeLabel = productTypeLabel;

  constructor() {
    this.load();
  }

  protected load(): void {
    this.failed.set(false);
    this.items.set(null);
    this.queries.list({ includeInactive: true, page: 1, sort: 'name,asc' }).subscribe({
      next: (page) => this.items.set(page.items),
      error: () => {
        this.items.set([]);
        this.failed.set(true);
      },
    });
  }
}
