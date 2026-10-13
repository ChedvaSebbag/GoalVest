import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, map, of, tap } from 'rxjs';
import { AuthCommandsService } from './auth-commands.service';
import { RegisterPayload, UserRole, homeRouteForRole } from './auth.models';
import { SessionRefresher } from './session-refresher';
import { TokenStore } from './token-store';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly commands = inject(AuthCommandsService);
  private readonly tokens = inject(TokenStore);
  private readonly refresher = inject(SessionRefresher);
  private readonly router = inject(Router);

  readonly user = this.tokens.user;

  login(email: string, password: string): Observable<UserRole> {
    return this.commands.login(email, password).pipe(
      tap((session) => this.tokens.setSession(session.accessToken, session.refreshToken, session.user)),
      map((session) => session.user.role),
    );
  }

  register(body: RegisterPayload): Observable<void> {
    return this.commands.register(body).pipe(map(() => undefined));
  }

  logout(): Observable<void> {
    const refreshToken = this.tokens.refreshToken();
    const clear = () => {
      this.tokens.clear();
      void this.router.navigateByUrl('/auth/login');
    };
    if (!refreshToken) {
      clear();
      return of(undefined);
    }
    return this.commands.logout(refreshToken).pipe(
      catchError(() => of(undefined)),
      tap(() => clear()),
      map(() => undefined),
    );
  }

  /** משחזר Access מ-Refresh אחרי רענון הדף. Guards שרצים במקביל חולקים את אותה קריאה. */
  ensureAccess(): Observable<boolean> {
    if (this.tokens.accessToken() && this.tokens.user()) {
      return of(true);
    }
    if (!this.tokens.refreshToken()) {
      return of(false);
    }
    return this.refresher.refresh().pipe(
      map(() => true),
      catchError(() => {
        this.tokens.clear();
        return of(false);
      }),
    );
  }

  homeForCurrentUser(): string {
    const role = this.tokens.user()?.role;
    return role ? homeRouteForRole(role) : '/auth/login';
  }
}
