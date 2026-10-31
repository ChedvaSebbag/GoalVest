// Lazy-loaded standalone components. Guards: authGuard (signed in), roleGuard (INVESTOR/AGENT),
// riskProfileGuard (investors complete the risk questionnaire first). Guards are UX only;
// authorization is enforced by the API (@require_role).
import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { riskProfileGuard } from './core/guards/risk-profile.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'auth/login' },
  { path: 'help', title: 'עזרה · GoalVest', loadComponent: () => import('./features/help/help-page').then(m => m.HelpPage) },
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
      { path: 'offers', canActivate: [riskProfileGuard], loadComponent: () => import('./features/investor/offers/offers-list').then(m => m.OffersList) },
      { path: 'offers/:id', canActivate: [riskProfileGuard], loadComponent: () => import('./features/investor/offers/offer-details').then(m => m.OfferDetailsPage) },
    ],
  },
  {
    path: 'products',
    canActivate: [authGuard],
    children: [
      { path: '', loadComponent: () => import('./features/products/catalog/catalog').then(m => m.Catalog) },
      { path: ':id', loadComponent: () => import('./features/products/product-details/product-details').then(m => m.ProductDetailsPage) },
    ],
  },
  {
    path: 'agent',
    canActivate: [authGuard, roleGuard('AGENT')],
    loadComponent: () => import('./features/agent/agent-home').then(m => m.AgentHome),
    children: [
      { path: '', loadComponent: () => import('./features/agent/agent-dashboard').then(m => m.AgentDashboard) },
      { path: 'leads/:id', loadComponent: () => import('./features/agent/lead/lead-details').then(m => m.LeadDetailsPage) },
      { path: 'products/new', loadComponent: () => import('./features/agent/products/product-form').then(m => m.ProductForm) },
      { path: 'products/:id/edit', loadComponent: () => import('./features/agent/products/product-form').then(m => m.ProductForm) },
      { path: 'products/:id/documents', loadComponent: () => import('./features/agent/products/product-documents').then(m => m.ProductDocuments) },
      { path: 'products', loadComponent: () => import('./features/agent/products/agent-products').then(m => m.AgentProducts) },
    ],
  },
  { path: '**', redirectTo: 'auth/login' },
];
