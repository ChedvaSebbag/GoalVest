import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'gv-agent-dashboard',
  imports: [RouterLink, MatButtonModule],
  template: `
    <section class="gv-page">
      <h1>דשבורד סוכן</h1>
      <p class="gv-muted">לידים ודשבורד יתווספו בהמשך. אפשר לנהל את המוצרים של הגוף כבר עכשיו.</p>
      <a mat-flat-button routerLink="/agent/products">המוצרים שלי</a>
    </section>
  `,
  styles: `h1 { margin: 0; color: var(--gv-primary); }`,
})
export class AgentDashboard {}
