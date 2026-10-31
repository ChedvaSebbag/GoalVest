// Query side of CQRS on the client: GET calls only, returning view-ready data built from rm_* tables.
import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  GoalDetails,
  GoalSummary,
  InstitutionOption,
  InvestorDashboard,
  InvestorProfileView,
  OfferView,
  TimelineItem,
} from './investor.models';

/** קריאה: פרופיל, יעדים, ציר זמן וגופים. */
@Injectable({ providedIn: 'root' })
export class InvestorQueriesService {
  private readonly http = inject(HttpClient);

  profile(): Observable<InvestorProfileView> {
    return this.http.get<InvestorProfileView>('/api/investor/profile');
  }

  goals(): Observable<{ items: GoalSummary[] }> {
    return this.http.get<{ items: GoalSummary[] }>('/api/investor/goals');
  }

  dashboard(): Observable<InvestorDashboard> {
    return this.http.get<InvestorDashboard>('/api/investor/dashboard');
  }

  offers(): Observable<{ items: OfferView[] }> {
    return this.http.get<{ items: OfferView[] }>('/api/investor/offers');
  }

  offer(offerId: string): Observable<OfferView> {
    return this.http.get<OfferView>(`/api/investor/offers/${offerId}`);
  }

  goal(goalId: string): Observable<GoalDetails> {
    return this.http.get<GoalDetails>(`/api/investor/goals/${goalId}`);
  }

  timeline(requestId: string): Observable<{ items: TimelineItem[] }> {
    return this.http.get<{ items: TimelineItem[] }>(`/api/requests/${requestId}/timeline`);
  }

  institutions(): Observable<{ items: InstitutionOption[] }> {
    return this.http.get<{ items: InstitutionOption[] }>('/api/institutions');
  }
}
