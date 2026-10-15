import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CommandResult } from '../investor/investor.models';

@Injectable({ providedIn: 'root' })
export class AgentCommandsService {
  private readonly http = inject(HttpClient);

  claim(requestId: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(`/api/agent/leads/${requestId}/claim`, {}, { headers: this.key() });
  }

  approve(requestId: string, note: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(
      `/api/agent/leads/${requestId}/assessment/approve`,
      { note },
      { headers: this.key() },
    );
  }

  reject(requestId: string, note: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(
      `/api/agent/leads/${requestId}/assessment/reject`,
      { note },
      { headers: this.key() },
    );
  }

  reevaluate(requestId: string, reason: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(
      `/api/agent/leads/${requestId}/reevaluate`,
      { reason },
      { headers: this.key() },
    );
  }

  sendOffer(
    requestId: string,
    items: { productId: string; percent: number }[],
    message: string,
  ): Observable<CommandResult> {
    return this.http.post<CommandResult>(
      `/api/agent/leads/${requestId}/offers`,
      { items, message },
      { headers: this.key() },
    );
  }

  private key(): { 'Idempotency-Key': string } {
    return { 'Idempotency-Key': crypto.randomUUID() };
  }
}
