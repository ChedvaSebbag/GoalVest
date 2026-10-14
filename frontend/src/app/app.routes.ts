import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { riskProfileGuard } from './core/guards/risk-profile.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'auth/login' },
  { path: 'system', loadComponent: () => import('./features/system-status/system-status').then(m => m.SystemStatus) },
  { path: 'auth/login', loadComponent: () => import('./features/auth/auth-page').then(m => m.AuthPage), data: { tab: 'login' } },
  { path: 'auth/register', loadComponent: () => import('./features/auth/auth-page').then(m => m.AuthPage), data: { tab: 'register' } },
  {
    path: 'investor',
    canActivate: [authGuard, roleGuard('INVESTOR')],
    loadComponent: () => import('./features/investor/investor-home').then(m => m.InvestorHome),
    children: [
      { path: 'risk', loadComponent: () => import('./features/investor/risk-quiz/risk-quiz').then(m => m.RiskQuiz) },
      { path: '', canActivate: [riskProfileGuard], loadComponent: () => import('./features/investor/dashboard/investor-dashboard').then(m => m.InvestorDashboard) },
      { path: 'goals/new', canActivate: [riskProfileGuard], loadComponent: () => import('./features/investor/goal-wizard/goal-wizard').then(m => m.GoalWizard) },
      { path: 'goals/:id/edit', canActivate: [riskProfileGuard], loadComponent: () => import('./features/investor/goal-wizard/goal-wizard').then(m => m.GoalWizard) },
      { path: 'goals/:id', canActivate: [riskProfileGuard], loadComponent: () => import('./features/investor/goal-details/goal-details').then(m => m.GoalDetailsPage) },
    ],
  },
  {
    path: 'agent',
    canActivate: [authGuard, roleGuard('AGENT')],
    loadComponent: () => import('./features/agent/agent-home').then(m => m.AgentHome),
  },
  { path: '**', redirectTo: 'auth/login' },
];
