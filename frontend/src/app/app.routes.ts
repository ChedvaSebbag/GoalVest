import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./features/system-status/system-status').then(m => m.SystemStatus) },
  { path: '**', redirectTo: '' },
];
