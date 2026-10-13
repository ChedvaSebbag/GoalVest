import { TestBed } from '@angular/core/testing';
import { homeRouteForRole } from './core/auth/auth.models';
import { InvestorHome } from './features/investor/investor-home';
import { AgentHome } from './features/agent/agent-home';

describe('auth routing', () => {
  it('sends an investor to /investor and an agent to /agent', () => {
    expect(homeRouteForRole('INVESTOR')).toBe('/investor');
    expect(homeRouteForRole('AGENT')).toBe('/agent');
  });
});

describe('role homes', () => {
  it('shows a title for each role', async () => {
    const investor = TestBed.createComponent(InvestorHome);
    await investor.whenStable();
    expect(investor.nativeElement.textContent).toContain('דשבורד משקיע');

    const agent = TestBed.createComponent(AgentHome);
    await agent.whenStable();
    expect(agent.nativeElement.textContent).toContain('דשבורד סוכן');
  });
});
