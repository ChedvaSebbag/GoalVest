import { HttpClient, HttpBackend, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, finalize, shareReplay, tap, throwError } from 'rxjs';
import { AuthSession } from './auth.models';
import { TokenStore } from './token-store';

/** קריאת refresh בלי לעבור ב-authInterceptor, כדי שלא תיווצר לולאה. */
@Injectable({ providedIn: 'root' })
export class SessionRefresher {
  private readonly http = new HttpClient(inject(HttpBackend));
  private readonly tokens = inject(TokenStore);
  private pending: Observable<AuthSession> | null = null;

  refresh(): Observable<AuthSession> {
    const refreshToken = this.tokens.refreshToken();
    if (!refreshToken) {
      return throwError(() => new HttpErrorResponse({ status: 401 }));
    }
    if (!this.pending) {
      this.pending = this.http.post<AuthSession>('/api/auth/refresh', { refreshToken }, {
        headers: { 'X-Correlation-Id': crypto.randomUUID() },
      }).pipe(
        tap((session) => this.tokens.setSession(session.accessToken, session.refreshToken, session.user)),
        finalize(() => { this.pending = null; }),
        shareReplay(1),
      );
    }
    return this.pending;
  }
}
