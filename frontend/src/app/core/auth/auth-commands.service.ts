import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AuthSession, RegisterPayload, RegisteredUser } from './auth.models';

/** כתיבה: הרשמה, התחברות, refresh ו-logout. */
@Injectable({ providedIn: 'root' })
export class AuthCommandsService {
  private readonly http = inject(HttpClient);

  register(body: RegisterPayload): Observable<RegisteredUser> {
    return this.http.post<RegisteredUser>('/api/auth/register', body, {
      headers: { 'Idempotency-Key': crypto.randomUUID() },
    });
  }

  login(email: string, password: string): Observable<AuthSession> {
    return this.http.post<AuthSession>('/api/auth/login', { email, password });
  }

  logout(refreshToken: string): Observable<void> {
    return this.http.post<void>('/api/auth/logout', { refreshToken });
  }
}
