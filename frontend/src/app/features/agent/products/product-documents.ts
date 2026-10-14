import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { ProductCommandsService } from '../../../core/products/product-commands.service';
import { ProductQueriesService } from '../../../core/products/product-queries.service';
import { DOC_TYPES, ProductDocument, apiError, docTypeLabel } from '../../../core/products/product.models';
import { StatusChip } from '../../../shared/status-chip';

const MAX_BYTES = 10 * 1024 * 1024;

@Component({
  selector: 'gv-product-documents',
  imports: [FormsModule, RouterLink, MatButtonModule, StatusChip],
  templateUrl: './product-documents.html',
  styleUrl: './product-documents.scss',
})
export class ProductDocuments {
  private readonly commands = inject(ProductCommandsService);
  private readonly queries = inject(ProductQueriesService);
  private readonly route = inject(ActivatedRoute);
  private readonly productId = this.route.snapshot.paramMap.get('id') ?? '';

  protected readonly docTypes = DOC_TYPES;
  protected readonly docTypeLabel = docTypeLabel;
  protected readonly items = signal<ProductDocument[] | null>(null);
  protected readonly failed = signal(false);
  protected readonly message = signal('');
  protected readonly uploading = signal(false);
  protected docType = 'POLICY_TERMS';
  protected file: File | null = null;

  constructor() {
    this.load();
  }

  protected load(): void {
    this.failed.set(false);
    this.items.set(null);
    this.queries.documents(this.productId).subscribe({
      next: (page) => this.items.set(page.items),
      error: () => {
        this.items.set([]);
        this.failed.set(true);
      },
    });
  }

  protected onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.file = input.files?.[0] ?? null;
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.file = event.dataTransfer?.files?.[0] ?? null;
  }

  protected upload(): void {
    if (!this.file) {
      this.message.set('יש לבחור קובץ PDF או DOCX.');
      return;
    }
    if (this.file.size > MAX_BYTES) {
      this.message.set('גודל הקובץ חייב להיות עד 10MB.');
      return;
    }
    this.uploading.set(true);
    this.message.set('');
    this.commands.upload(this.productId, this.file, this.docType).subscribe({
      next: () => {
        this.uploading.set(false);
        this.file = null;
        this.message.set('המסמך נשמר וממתין להטמעה.');
        this.load();
      },
      error: (error: unknown) => {
        this.uploading.set(false);
        this.message.set(apiError(error).message);
      },
    });
  }
}
