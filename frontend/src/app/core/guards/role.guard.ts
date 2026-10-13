import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { UserRole, homeRouteForRole } from '../auth/auth.models';
import { AuthService } from '../auth/auth.service';

export const roleGuard = (role: UserRole): CanActivateFn => () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.ensureAccess().pipe(
    map((ok) => {
      if (!ok) {
        return router.createUrlTree(['/auth/login']);
      }
      const current = auth.user()?.role;
      if (current === role) {
        return true;
      }
      return router.createUrlTree([current ? homeRouteForRole(current) : '/auth/login']);
    }),
  );
};
