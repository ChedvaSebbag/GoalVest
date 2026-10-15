import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';

export interface NextStep {
  icon: string;
  title: string;
  text: string;
  /** כפתור פעולה: קישור (link) או אירוע (action) */
  cta?: { label: string; link?: (string | number)[] | string };
  tone?: 'info' | 'success' | 'warning';
}

/** כרטיס "הצעד הבא" בראש הדשבורד: אומר למשתמש מה המצב ומה כדאי לעשות עכשיו. */
@Component({
  selector: 'gv-next-step',
  imports: [RouterLink, MatButtonModule],
  template: `
    <aside class="next" [attr.data-tone]="step().tone ?? 'info'" role="status" aria-live="polite">
      <span class="icon material-symbols-rounded" aria-hidden="true">{{ step().icon }}</span>
      <div class="body">
        <p class="label">הצעד הבא</p>
        <h2>{{ step().title }}</h2>
        <p>{{ step().text }}</p>
      </div>
      @if (step().cta; as cta) {
        @if (cta.link) {
          <a mat-flat-button [routerLink]="cta.link">{{ cta.label }}</a>
        } @else {
          <button type="button" mat-flat-button (click)="action.emit()">{{ cta.label }}</button>
        }
      }
    </aside>
  `,
  styles: `
    .next {
      --tone: var(--gv-primary);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: calc(var(--gv-space) * 2);
      padding: calc(var(--gv-space) * 2) calc(var(--gv-space) * 3);
      margin-block-end: calc(var(--gv-space) * 3);
      border-radius: var(--gv-radius);
      border-inline-start: 6px solid var(--tone);
      background: color-mix(in srgb, var(--tone) 8%, var(--gv-surface));
      box-shadow: var(--gv-shadow);
    }
    .next[data-tone='success'] { --tone: var(--gv-success); }
    .next[data-tone='warning'] { --tone: var(--gv-warning); }
    .icon { font-size: 36px; color: var(--tone); }
    .body { flex: 1; min-inline-size: 200px; }
    .label { margin: 0; font-size: 0.8rem; font-weight: 700; color: var(--tone); }
    h2 { margin: 2px 0 4px; font-size: 1.15rem; color: var(--gv-text); }
    p { margin: 0; color: var(--gv-text-muted); }
  `,
})
export class NextStepCard {
  readonly step = input.required<NextStep>();
  readonly action = output<void>();
}
