import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatPaginatorIntl, MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { AuthQueriesService } from '../../../core/auth/auth-queries.service';
import { Institution } from '../../../core/auth/auth.models';
import { ProductQueriesService } from '../../../core/products/product-queries.service';
import {
  CHANNELS,
  LIQUIDITY_OPTIONS,
  ProductSummary,
  formatPercent,
  liquidityLabel,
  productTypeLabel,
  riskLabel,
} from '../../../core/products/product.models';

function hebrewPaginator(): MatPaginatorIntl {
  const intl = new MatPaginatorIntl();
  intl.itemsPerPageLabel = 'בעמוד';
  intl.nextPageLabel = 'העמוד הבא';
  intl.previousPageLabel = 'העמוד הקודם';
  intl.firstPageLabel = 'העמוד הראשון';
  intl.lastPageLabel = 'העמוד האחרון';
  intl.getRangeLabel = (page, pageSize, length) => {
    if (length === 0) {
      return '0 מתוך 0';
    }
    const start = page * pageSize + 1;
    const end = Math.min((page + 1) * pageSize, length);
    return `${start}–${end} מתוך ${length}`;
  };
  return intl;
}

import { InfoTip } from '../../../shared/info-tip';

@Component({
  selector: 'gv-catalog',
  imports: [FormsModule, RouterLink, MatButtonModule, MatTableModule, MatSortModule, MatPaginatorModule, InfoTip],
  providers: [{ provide: MatPaginatorIntl, useFactory: hebrewPaginator }],
  templateUrl: './catalog.html',
  styleUrl: './catalog.scss',
})
export class Catalog {
  private readonly queries = inject(ProductQueriesService);
  private readonly authQueries = inject(AuthQueriesService);
  private readonly route = inject(ActivatedRoute);

  protected readonly channels = CHANNELS;
  protected readonly liquidityOptions = LIQUIDITY_OPTIONS;
  protected readonly columns = [
    'select', 'type', 'name', 'institution', 'track',
    'return1y', 'return3y', 'return5y', 'feeAssets', 'feeDeposit', 'stdDev', 'liquidity', 'riskLevel',
  ];
  protected readonly productTypeLabel = productTypeLabel;
  protected readonly liquidityLabel = liquidityLabel;
  protected readonly riskLabel = riskLabel;
  protected readonly formatPercent = formatPercent;

  protected readonly items = signal<ProductSummary[] | null>(null);
  protected readonly total = signal(0);
  protected readonly failed = signal(false);
  protected readonly pageIndex = signal(0);
  protected readonly institutions = signal<Institution[]>([]);
  protected readonly selected = signal<ProductSummary[]>([]);
  protected readonly compareOpen = signal(false);

  protected q = this.route.snapshot.queryParamMap.get('q') ?? '';
  protected selectedTypes = new Set<string>();
  protected riskMin: number | null = null;
  protected riskMax: number | null = null;
  protected maxFee = '';
  protected minReturn3y = '';
  protected liquidity = '';
  protected institutionId = '';
  protected sort = 'name,asc';

  constructor() {
    this.authQueries.institutions().subscribe({
      next: (items) => this.institutions.set(items),
      error: () => this.institutions.set([]),
    });
    this.load();
  }

  protected load(): void {
    this.failed.set(false);
    this.items.set(null);
    this.queries.list({
      q: this.q.trim(),
      types: [...this.selectedTypes],
      riskMin: this.riskMin,
      riskMax: this.riskMax,
      maxFee: this.maxFee.trim(),
      minReturn3y: this.minReturn3y.trim(),
      liquidity: this.liquidity,
      institutionId: this.institutionId,
      page: this.pageIndex() + 1,
      sort: this.sort,
    }).subscribe({
      next: (page) => {
        this.items.set(page.items);
        this.total.set(page.total);
      },
      error: () => {
        this.items.set([]);
        this.failed.set(true);
      },
    });
  }

  protected apply(): void {
    this.pageIndex.set(0);
    this.load();
  }

  protected clear(): void {
    this.q = '';
    this.selectedTypes.clear();
    this.riskMin = null;
    this.riskMax = null;
    this.maxFee = '';
    this.minReturn3y = '';
    this.liquidity = '';
    this.institutionId = '';
    this.apply();
  }

  protected toggleType(id: string): void {
    if (this.selectedTypes.has(id)) {
      this.selectedTypes.delete(id);
    } else {
      this.selectedTypes.add(id);
    }
    this.apply();
  }

  protected onPage(event: PageEvent): void {
    this.pageIndex.set(event.pageIndex);
    this.load();
  }

  protected onSort(event: Sort): void {
    this.sort = event.direction ? `${event.active},${event.direction}` : 'name,asc';
    this.pageIndex.set(0);
    this.load();
  }

  protected isSelected(product: ProductSummary): boolean {
    return this.selected().some((item) => item.productId === product.productId);
  }

  protected selectionFull(product: ProductSummary): boolean {
    return this.selected().length >= 4 && !this.isSelected(product);
  }

  protected toggle(product: ProductSummary, checked: boolean): void {
    if (checked) {
      if (this.selected().length >= 4) {
        return;
      }
      this.selected.update((items) => [...items, product]);
      return;
    }
    this.selected.update((items) => items.filter((item) => item.productId !== product.productId));
  }

  protected openCompare(): void {
    this.compareOpen.set(true);
  }

  protected signedClass(value: string): string {
    const amount = Number(value);
    if (amount > 0) {
      return 'pos';
    }
    if (amount < 0) {
      return 'neg';
    }
    return '';
  }
}
