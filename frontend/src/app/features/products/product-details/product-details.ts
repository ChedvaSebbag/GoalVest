import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatTabsModule } from '@angular/material/tabs';
import { ProductQueriesService } from '../../../core/products/product-queries.service';
import {
  ProductDetails,
  docTypeLabel,
  formatPercent,
  liquidityLabel,
  productTypeLabel,
  riskLabel,
} from '../../../core/products/product.models';
import { Disclaimer } from '../../../shared/disclaimer';
import { MoneyPipe } from '../../../shared/money.pipe';

@Component({
  selector: 'gv-product-details',
  imports: [RouterLink, MatButtonModule, MatTabsModule, MoneyPipe, Disclaimer],
  templateUrl: './product-details.html',
  styleUrl: './product-details.scss',
})
export class ProductDetailsPage {
  private readonly queries = inject(ProductQueriesService);
  private readonly route = inject(ActivatedRoute);

  protected readonly product = signal<ProductDetails | null>(null);
  protected readonly failed = signal(false);
  protected readonly productTypeLabel = productTypeLabel;
  protected readonly liquidityLabel = liquidityLabel;
  protected readonly riskLabel = riskLabel;
  protected readonly docTypeLabel = docTypeLabel;
  protected readonly formatPercent = formatPercent;

  constructor() {
    this.load();
  }

  protected load(): void {
    const productId = this.route.snapshot.paramMap.get('id');
    if (!productId) {
      this.failed.set(true);
      this.product.set(null);
      return;
    }
    this.failed.set(false);
    this.product.set(null);
    this.queries.get(productId).subscribe({
      next: (item) => this.product.set(item),
      error: () => {
        this.product.set(null);
        this.failed.set(true);
      },
    });
  }

  protected bars(item: ProductDetails): { label: string; value: string; width: number; negative: boolean }[] {
    const points = [
      { label: 'שנה', value: item.return1y },
      { label: '3 שנים', value: item.return3y },
      { label: '5 שנים', value: item.return5y },
    ];
    const max = Math.max(1, ...points.map((point) => Math.abs(Number(point.value)) || 0));
    return points.map((point) => {
      const amount = Number(point.value);
      return {
        label: point.label,
        value: point.value,
        width: Math.min(100, (Math.abs(amount) / max) * 100),
        negative: amount < 0,
      };
    });
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

  protected download(documentId: string, fileName: string): void {
    this.queries.download(documentId).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        link.click();
        URL.revokeObjectURL(url);
      },
    });
  }
}
