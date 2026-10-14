import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CommandResult } from '../investor/investor.models';
import { ProductWrite } from './product.models';

/** כתיבה: יצירה, עדכון, השבתה והעלאת מסמך. */
@Injectable({ providedIn: 'root' })
export class ProductCommandsService {
  private readonly http = inject(HttpClient);

  create(body: ProductWrite): Observable<CommandResult> {
    return this.http.post<CommandResult>('/api/agent/products', body, { headers: this.key() });
  }

  update(productId: string, body: ProductWrite): Observable<CommandResult> {
    return this.http.put<CommandResult>(`/api/agent/products/${productId}`, body, { headers: this.key() });
  }

  deactivate(productId: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(`/api/agent/products/${productId}/deactivate`, {}, { headers: this.key() });
  }

  upload(productId: string, file: File, docType: string): Observable<CommandResult> {
    const body = new FormData();
    body.append('file', file);
    body.append('docType', docType);
    return this.http.post<CommandResult>(`/api/agent/products/${productId}/documents`, body, { headers: this.key() });
  }

  private key(): { 'Idempotency-Key': string } {
    return { 'Idempotency-Key': crypto.randomUUID() };
  }
}
