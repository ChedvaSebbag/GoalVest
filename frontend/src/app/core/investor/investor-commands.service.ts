// Command side of CQRS on the client: write calls only (POST/PUT) returning {id, version}.
// Each call sends a fresh Idempotency-Key so a double click cannot create duplicates.
// Reads live in investor-queries.service.ts.
import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CommandResult, GoalWrite } from './investor.models';

/** כתיבה: פרופיל, שאלון, יעדים ובקשות. */
@Injectable({ providedIn: 'root' })
export class InvestorCommandsService {
  private readonly http = inject(HttpClient);

  assess(answers: Record<string, unknown>): Observable<CommandResult> {
    return this.http.post<CommandResult>('/api/investor/risk-assessment', { answers }, { headers: this.key() });
  }

  createGoal(body: GoalWrite): Observable<CommandResult> {
    return this.http.post<CommandResult>('/api/investor/goals', body, { headers: this.key() });
  }

  updateGoal(goalId: string, body: GoalWrite & { consentShareContact: boolean }): Observable<CommandResult> {
    return this.http.put<CommandResult>(`/api/investor/goals/${goalId}`, body, { headers: this.key() });
  }

  archiveGoal(goalId: string): Observable<CommandResult> {
    return this.http.delete<CommandResult>(`/api/investor/goals/${goalId}`, { headers: this.key() });
  }

  submitRequest(goalId: string, consentShareContact: boolean): Observable<CommandResult> {
    return this.http.post<CommandResult>('/api/requests', { goalId, consentShareContact }, { headers: this.key() });
  }

  acceptOffer(offerId: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(`/api/investor/offers/${offerId}/accept`, {}, { headers: this.key() });
  }

  declineOffer(offerId: string, reason: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(
      `/api/investor/offers/${offerId}/decline`,
      { reason },
      { headers: this.key() },
    );
  }

  cancelRequest(requestId: string, reason: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(`/api/requests/${requestId}/cancel`, { reason }, { headers: this.key() });
  }

  private key(): { 'Idempotency-Key': string } {
    return { 'Idempotency-Key': crypto.randomUUID() };
  }
}
