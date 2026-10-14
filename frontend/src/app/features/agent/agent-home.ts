import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'gv-agent-home',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <nav class="nav">
      <a routerLink="/agent" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">דשבורד סוכן</a>
      <a routerLink="/agent/products" routerLinkActive="active">המוצרים שלי</a>
      <a routerLink="/products" routerLinkActive="active">קטלוג</a>
    </nav>
    <router-outlet />
  `,
  styles: `
    .nav {
      display: flex;
      gap: calc(var(--gv-space) * 2);
      padding: calc(var(--gv-space) * 2) calc(var(--gv-space) * 3);
      background: var(--gv-surface);
      box-shadow: var(--gv-shadow);
    }
    a { color: var(--gv-primary); text-decoration: none; }
    .active { font-weight: 700; }
  `,
})
export class AgentHome {}
