import { Component } from '@angular/core';

@Component({
  selector: 'gv-investor-home',
  template: `
    <section class="page">
      <h1>דשבורד משקיע</h1>
      <p class="muted">התוכן יוצג כאן בהמשך.</p>
    </section>
  `,
  styles: `
    .page { max-width: 720px; margin: calc(var(--gv-space) * 4) auto; padding-inline: calc(var(--gv-space) * 2); }
    h1 { margin: 0; color: var(--gv-primary); }
    .muted { color: var(--gv-text-muted); }
  `,
})
export class InvestorHome {}
