// Adds the Bearer access token to every API call. On 401 it refreshes the session once and
// retries the request; if that fails the user is sent to login. correlation.interceptor.ts adds
// X-Correlation-Id for tracing a request across logs.
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { SessionRefresher } from '../auth/session-refresher';
import { TokenStore } from '../auth/token-store';

const SKIP = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh'];

/** מוסיף Bearer, ומנסה refresh פעם אחת כשהשרת מחזיר 401. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const tokens = inject(TokenStore);
  const refresher = inject(SessionRefresher);
  const router = inject(Router);
  const skipped = SKIP.some((path) => req.url.includes(path));
  const access = tokens.accessToken();
  const outgoing = !skipped && access
    ? req.clone({ setHeaders: { Authorization: `Bearer ${access}` } })
    : req;

  return next(outgoing).pipe(
    catchError((error: unknown) => {
      const status = error instanceof HttpErrorResponse ? error.status : 0;
      const retried = req.headers.has('X-Auth-Retry');
      if (status !== 401 || skipped || retried || !tokens.refreshToken()) {
        return throwError(() => error);
      }
      return refresher.refresh().pipe(
        switchMap(() => {
          const renewed = tokens.accessToken();
          const retry = req.clone({
            setHeaders: {
              Authorization: `Bearer ${renewed ?? ''}`,
              'X-Auth-Retry': '1',
            },
          });
          return next(retry);
        }),
        catchError((refreshError: unknown) => {
          tokens.clear();
          void router.navigateByUrl('/auth/login');
          return throwError(() => refreshError);
        }),
      );
    }),
  );
};
