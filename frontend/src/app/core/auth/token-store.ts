import { Injectable, signal } from '@angular/core';
import { SessionUser } from './auth.models';

const REFRESH_KEY = 'gv_refresh_token';

/** Access והמשתמש בזיכרון. Refresh ב-localStorage, לפי docs/12 §12.1. */
@Injectable({ providedIn: 'root' })
export class TokenStore {
  readonly accessToken = signal<string | null>(null);
  readonly user = signal<SessionUser | null>(null);

  refreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  setSession(accessToken: string, refreshToken: string, user: SessionUser): void {
    this.accessToken.set(accessToken);
    this.user.set(user);
    localStorage.setItem(REFRESH_KEY, refreshToken);
  }

  clear(): void {
    this.accessToken.set(null);
    this.user.set(null);
    localStorage.removeItem(REFRESH_KEY);
  }
}
