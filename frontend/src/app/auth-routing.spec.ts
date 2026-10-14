import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { homeRouteForRole } from './core/auth/auth.models';
import { AgentHome } from './features/agent/agent-home';
import { InvestorDashboard } from './features/investor/dashboard/investor-dashboard';

describe('auth routing', () => {
  it('sends an investor to /investor and an agent to /agent', () => {
    expect(homeRouteForRole('INVESTOR')).toBe('/investor');
    expect(homeRouteForRole('AGENT')).toBe('/agent');
  });
});

describe('role homes', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
  });

  it('shows a title for each role', async () => {
    const investor = TestBed.createComponent(InvestorDashboard);
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/investor/goals').flush({ items: [] });
    await investor.whenStable();
    expect(investor.nativeElement.textContent).toContain('דשבורד משקיע');

    const agent = TestBed.createComponent(AgentHome);
    await agent.whenStable();
    expect(agent.nativeElement.textContent).toContain('דשבורד סוכן');
    http.verify();
  });
});
