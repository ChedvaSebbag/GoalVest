import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ProductCommandsService } from '../../../core/products/product-commands.service';
import { ProductQueriesService } from '../../../core/products/product-queries.service';
import {
  LIQUIDITY_OPTIONS,
  PRODUCT_TYPES,
  ProductWrite,
  apiError,
  isMarketType,
} from '../../../core/products/product.models';

@Component({
  selector: 'gv-product-form',
  imports: [ReactiveFormsModule, RouterLink, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  templateUrl: './product-form.html',
  styleUrl: './product-form.scss',
})
export class ProductForm {
  private readonly commands = inject(ProductCommandsService);
  private readonly queries = inject(ProductQueriesService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly types = PRODUCT_TYPES;
  protected readonly liquidityOptions = LIQUIDITY_OPTIONS;
  protected readonly levels = [1, 2, 3, 4, 5, 6, 7];
  protected readonly productId = this.route.snapshot.paramMap.get('id');
  protected readonly failed = signal(false);
  protected readonly submitting = signal(false);
  protected readonly message = signal('');
  protected readonly fieldErrors = signal<Record<string, string>>({});
  protected readonly isActive = signal(true);
  protected readonly institutionName = signal('');
  protected readonly market = signal(false);

  protected readonly form = this.formBuilder.nonNullable.group({
    type: ['HISHTALMUT', Validators.required],
    name: ['', [Validators.required, Validators.minLength(2)]],
    track: ['', Validators.required],
    symbol: [''],
    feeDeposit: ['0.00', Validators.required],
    feeAssets: ['0.00', Validators.required],
    return1y: ['0.00', Validators.required],
    return3y: ['0.00', Validators.required],
    return5y: ['0.00', Validators.required],
    stdDev: ['0.00', Validators.required],
    riskLevel: [3, [Validators.required, Validators.min(1), Validators.max(7)]],
    liquidity: ['PARTIAL', Validators.required],
    liquidityTerms: ['', [Validators.required, Validators.minLength(2)]],
    taxNotes: ['', [Validators.required, Validators.minLength(2)]],
    minDeposit: ['0.00', Validators.required],
    description: ['', [Validators.required, Validators.minLength(2)]],
  });

  constructor() {
    this.market.set(isMarketType(this.form.controls.type.value));
    this.form.controls.type.valueChanges.subscribe((value) => this.market.set(isMarketType(value)));
    if (this.productId) {
      this.queries.get(this.productId).subscribe({
        next: (product) => {
          this.institutionName.set(product.institutionName);
          this.isActive.set(product.isActive);
          this.form.patchValue({
            type: product.type,
            name: product.name,
            track: product.track,
            symbol: product.symbol ?? '',
            feeDeposit: product.feeDeposit,
            feeAssets: product.feeAssets,
            return1y: product.return1y,
            return3y: product.return3y,
            return5y: product.return5y,
            stdDev: product.stdDev,
            riskLevel: product.riskLevel,
            liquidity: product.liquidity,
            liquidityTerms: product.liquidityTerms,
            taxNotes: product.taxNotes,
            minDeposit: product.minDeposit,
            description: product.description,
          });
        },
        error: () => this.failed.set(true),
      });
    }
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const body: ProductWrite = {
      ...value,
      symbol: isMarketType(value.type) ? value.symbol.trim() : null,
    };
    this.submitting.set(true);
    this.message.set('');
    this.fieldErrors.set({});
    const request = this.productId
      ? this.commands.update(this.productId, body)
      : this.commands.create(body);
    request.subscribe({
      next: (result) => {
        this.submitting.set(false);
        if (!this.productId) {
          void this.router.navigate(['/agent/products', result.id, 'documents']);
          return;
        }
        this.message.set('המוצר נשמר.');
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        const parsed = apiError(error);
        this.message.set(parsed.message);
        this.fieldErrors.set(parsed.fields);
      },
    });
  }

  protected deactivate(): void {
    if (!this.productId) {
      return;
    }
    this.commands.deactivate(this.productId).subscribe({
      next: () => {
        this.isActive.set(false);
        this.message.set('המוצר הושבת ולא יופיע בקטלוג.');
      },
      error: (error: unknown) => this.message.set(apiError(error).message),
    });
  }
}
