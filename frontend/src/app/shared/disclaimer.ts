import { Component } from '@angular/core';

@Component({
  selector: 'gv-disclaimer',
  template: `<p>ההערכה נוצרה אוטומטית ואינה מהווה ייעוץ השקעות.</p>`,
  styles: `
    p { margin: calc(var(--gv-space) * 2) 0 0; color: var(--gv-text-muted); font-size: 0.85rem; }
  `,
})
export class Disclaimer {}
