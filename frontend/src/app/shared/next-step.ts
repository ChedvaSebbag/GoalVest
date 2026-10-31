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
      padding: calc(var(--gv-space) * 2.5) calc(var(--gv-space) * 3);
      margin-block-end: calc(var(--gv-space) * 3);
      border-radius: var(--gv-radius);
      border: 1px solid color-mix(in srgb, var(--tone) 25%, var(--gv-border));
      background: color-mix(in srgb, var(--tone) 6%, var(--gv-surface));
    }
    .next[data-tone='success'] { --tone: var(--gv-success); }
    .next[data-tone='warning'] { --tone: var(--gv-warning); }
    .icon {
      display: grid;
      place-items: center;
      inline-size: 48px !important;
      block-size: 48px;
      border-radius: 14px;
      background: var(--gv-surface);
      color: var(--tone);
      font-size: 28px;
      box-shadow: var(--gv-shadow);
    }
    .body { flex: 1; min-inline-size: 220px; }
    .label { margin: 0; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.3px; color: var(--tone); }
    h2 { margin: 2px 0; font-size: 1.1rem; color: var(--gv-text); }
    p { margin: 0; color: var(--gv-text-muted); }
  `,
})
export class NextStepCard {
  readonly step = input.required<NextStep>();
  readonly action = output<void>();
}
