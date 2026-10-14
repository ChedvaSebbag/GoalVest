import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';
import { firstValueFrom, isObservable } from 'rxjs';
import { riskProfileGuard } from './risk-profile.guard';

describe('riskProfileGuard', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
  });

  it('sends an investor without a score to the quiz', async () => {
    const pending = activate();
    TestBed.inject(HttpTestingController).expectOne('/api/investor/profile').flush({ riskScore: null });
    const result = await pending;
    expect(result).toBeInstanceOf(UrlTree);
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/investor/risk');
  });

  it('allows an investor who already has a score', async () => {
    const pending = activate();
    TestBed.inject(HttpTestingController).expectOne('/api/investor/profile').flush({ riskScore: 3 });
    expect(await pending).toBe(true);
  });
});

function activate() {
  const outcome = TestBed.runInInjectionContext(() =>
    riskProfileGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot),
  );
  if (!isObservable(outcome)) {
    throw new Error('expected an observable guard result');
  }
  return firstValueFrom(outcome);
}
