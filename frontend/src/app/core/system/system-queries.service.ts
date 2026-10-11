import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type ComponentStatus = 'ok' | 'error';

export interface HealthCheck {
  status: ComponentStatus;
  detail?: string;
}

export interface HealthResponse {
  status: ComponentStatus;
  checks: Record<'database' | 'ollama' | 'chroma', HealthCheck>;
}

/** צד השאילתות (Query) של מודול המערכת – לפי Rule R1, קריאות GET בלבד. */
@Injectable({ providedIn: 'root' })
export class SystemQueriesService {
  private readonly http = inject(HttpClient);

  getHealth(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>('/api/health');
  }
}
