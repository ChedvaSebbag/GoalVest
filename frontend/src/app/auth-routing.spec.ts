import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { homeRouteForRole } from './core/auth/auth.models';
import { journeyIndex, STATUS_HELP } from './core/help/help-content';
import { STATUS_LABELS } from './core/investor/investor.models';
import { HelpPage } from './features/help/help-page';
import { InvestorDashboard } from './features/investor/dashboard/investor-dashboard';
import { RequestJourney } from './shared/request-journey';

describe('auth routing', () => {
  it('sends an investor to /investor and an agent to /agent', () => {
    expect(homeRouteForRole('INVESTOR')).toBe('/investor');
    expect(homeRouteForRole('AGENT')).toBe('/agent');
  });
});

describe('user guidance', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
  });

  it('investor dashboard without goals shows the next step', async () => {
    const investor = TestBed.createComponent(InvestorDashboard);
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/investor/dashboard').flush({ plannedCapital: '0.00', activeGoals: 0, pendingOffers: 0, goals: [] });
    await investor.whenStable();
    const text = investor.nativeElement.textContent as string;
    expect(text).toContain('שלום');
    expect(text).toContain('הצעד הבא');
    expect(text).toContain('להגדיר את היעד הראשון');
    http.verify();
  });

  it('every request status has a label and an explanation', () => {
    for (const status of ['SUBMITTED', 'AI_PROCESSING', 'AI_EVALUATED', 'IN_REVIEW', 'REEVALUATION_REQUESTED', 'OFFER_SENT', 'ACCEPTED', 'CANCELLED', 'FAILED']) {
      expect(STATUS_LABELS[status]).toBeTruthy();
      expect(STATUS_HELP[status]?.investor).toBeTruthy();
      expect(STATUS_HELP[status]?.agent).toBeTruthy();
    }
    expect(journeyIndex('AI_PROCESSING')).toBe(1);
    expect(journeyIndex('FAILED')).toBe(-1);
  });

  it('request journey marks the current step and explains it', async () => {
    const journey = TestBed.createComponent(RequestJourney);
    journey.componentRef.setInput('status', 'IN_REVIEW');
    await journey.whenStable();
    const current = journey.nativeElement.querySelector('[aria-current="step"]') as HTMLElement;
    expect(current.textContent).toContain('בדיקת סוכן');
    expect(journey.nativeElement.textContent).toContain(STATUS_HELP['IN_REVIEW'].investor);
  });

  it('help page renders the guide', async () => {
    const help = TestBed.createComponent(HelpPage);
    await help.whenStable();
    const text = help.nativeElement.textContent as string;
    expect(text).toContain('מרכז העזרה');
    expect(text).toContain('איך GoalVest עובד');
  });
});
