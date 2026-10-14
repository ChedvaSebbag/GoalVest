import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ProductDetails, ProductDocument, ProductPage, ProductQuery } from './product.models';

/** קריאה: קטלוג, פרטי מוצר ומסמכים. */
@Injectable({ providedIn: 'root' })
export class ProductQueriesService {
  private readonly http = inject(HttpClient);

  list(query: ProductQuery = {}): Observable<ProductPage> {
    let params = new HttpParams()
      .set('page', String(query.page ?? 1))
      .set('pageSize', '20')
      .set('sort', query.sort ?? 'name,asc');
    if (query.q) {
      params = params.set('q', query.q);
    }
    for (const type of query.types ?? []) {
      params = params.append('type', type);
    }
    if (query.riskMin) {
      params = params.set('riskMin', String(query.riskMin));
    }
    if (query.riskMax) {
      params = params.set('riskMax', String(query.riskMax));
    }
    if (query.maxFee) {
      params = params.set('maxFee', query.maxFee);
    }
    if (query.minReturn3y) {
      params = params.set('minReturn3y', query.minReturn3y);
    }
    if (query.liquidity) {
      params = params.set('liquidity', query.liquidity);
    }
    if (query.institutionId) {
      params = params.set('institutionId', query.institutionId);
    }
    if (query.includeInactive) {
      params = params.set('includeInactive', 'true');
    }
    return this.http.get<ProductPage>('/api/products', { params });
  }

  get(productId: string): Observable<ProductDetails> {
    return this.http.get<ProductDetails>(`/api/products/${productId}`);
  }

  documents(productId: string): Observable<{ items: ProductDocument[] }> {
    return this.http.get<{ items: ProductDocument[] }>(`/api/agent/products/${productId}/documents`);
  }

  download(documentId: string): Observable<Blob> {
    return this.http.get(`/api/documents/${documentId}/download`, { responseType: 'blob' });
  }
}
