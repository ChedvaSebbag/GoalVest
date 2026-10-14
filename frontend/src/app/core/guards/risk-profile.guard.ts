import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { InvestorQueriesService } from '../investor/investor-queries.service';

/** משקיע בלי ציון סיכון מועבר לשאלון. */
export const riskProfileGuard: CanActivateFn = () => {
  const queries = inject(InvestorQueriesService);
  const router = inject(Router);
  return queries.profile().pipe(
    map((profile) => profile.riskScore != null || router.createUrlTree(['/investor/risk'])),
    catchError(() => of(router.createUrlTree(['/investor/risk']))),
  );
};
