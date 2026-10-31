import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AgentDashboard, LeadDetails, LeadPage, ProductInterest } from './agent.models';

@Injectable({ providedIn: 'root' })
export class AgentQueriesService {
  private readonly http = inject(HttpClient);

  dashboard(): Observable<AgentDashboard> {
    return this.http.get<AgentDashboard>('/api/agent/dashboard');
  }

  interest(): Observable<{ items: ProductInterest[] }> {
    return this.http.get<{ items: ProductInterest[] }>('/api/agent/dashboard/product-interest');
  }

  leads(filters: {
    status: string;
    minScore: string;
    goalType: string;
    page: number;
    since: string | null;
  }): Observable<LeadPage> {
    let params = new HttpParams().set('page', filters.page).set('sort', 'createdAt,desc');
    if (filters.status) {
      params = params.set('status', filters.status);
    }
    if (filters.minScore.trim()) {
      params = params.set('minScore', filters.minScore.trim());
    }
    if (filters.goalType) {
      params = params.set('goalType', filters.goalType);
    }
    if (filters.since) {
      params = params.set('since', filters.since);
    }
    return this.http.get<LeadPage>('/api/agent/leads', { params });
  }

  lead(requestId: string): Observable<LeadDetails> {
    return this.http.get<LeadDetails>(`/api/agent/leads/${requestId}`);
  }
}
