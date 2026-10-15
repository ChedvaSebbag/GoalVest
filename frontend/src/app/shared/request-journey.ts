import { Component, computed, input } from '@angular/core';
import { JOURNEY_STEPS, STATUS_HELP, journeyIndex } from '../core/help/help-content';
import { STATUS_LABELS } from '../core/investor/investor.models';

/**
 * מסלול הבקשה: חמישה שלבים (הגשה → הערכת AI → בדיקת סוכן → הצעה → סיום),
 * השלב הנוכחי מודגש, ומתחת מוסבר מה קורה עכשיו ומי צריך לפעול.
 */
@Component({
  selector: 'gv-request-journey',
  template: `
    <ol class="journey" [attr.aria-label]="'מסלול הבקשה. סטטוס נוכחי: ' + label()">
      @for (step of steps; track step.label; let i = $index) {
        <li
          [class.done]="!stopped() && i < current()"
          [class.now]="!stopped() && i === current()"
          [attr.aria-current]="!stopped() && i === current() ? 'step' : null"
        >
          <span class="dot material-symbols-rounded" aria-hidden="true">{{ !stopped() && i < current() ? 'check' : step.icon }}</span>
          <span class="name">{{ step.label }}</span>
        </li>
      }
    </ol>
    @if (help(); as info) {
      <div class="explain" [class.stopped]="stopped()">
        <p><strong>{{ label() }}:</strong> {{ view() === 'agent' ? info.agent : info.investor }}</p>
        @if (info.owner !== '—') {
          <p class="owner">מי צריך לפעול עכשיו: <strong>{{ info.owner }}</strong></p>
        }
      </div>
    }
  `,
  styles: `
    .journey {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      list-style: none;
      margin: calc(var(--gv-space) * 2) 0;
      padding: 0;
      counter-reset: none;
    }
    li {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      text-align: center;
      color: var(--gv-text-muted);
      font-size: 0.85rem;
    }
    li::before {
      content: '';
      position: absolute;
      inset-block-start: 17px;
      inset-inline-start: calc(-50% + 20px);
      inline-size: calc(100% - 40px);
      block-size: 2px;
      background: var(--gv-skeleton);
    }
    li:first-child::before { display: none; }
    li.done::before, li.now::before { background: var(--gv-primary); }
    .dot {
      display: grid;
      place-items: center;
      inline-size: 36px;
      block-size: 36px;
      border-radius: 50%;
      background: var(--gv-skeleton);
      color: var(--gv-text-muted);
      font-size: 20px;
    }
    li.done .dot { background: var(--gv-primary); color: var(--gv-on-primary); }
    li.now .dot {
      background: var(--gv-accent);
      color: var(--gv-text);
      box-shadow: 0 0 0 4px color-mix(in srgb, var(--gv-accent) 30%, transparent);
    }
    li.now .name { color: var(--gv-text); font-weight: 700; }
    .explain {
      padding: calc(var(--gv-space) * 1.5) calc(var(--gv-space) * 2);
      border-radius: calc(var(--gv-radius) / 1.5);
      background: var(--gv-bg);
    }
    .explain.stopped { background: color-mix(in srgb, var(--gv-error) 8%, var(--gv-surface)); }
    .explain p { margin: 0; }
    .owner { margin-block-start: 4px !important; font-size: 0.9rem; color: var(--gv-text-muted); }
    @media (max-width: 520px) {
      .name { font-size: 0.75rem; }
      .dot { inline-size: 30px; block-size: 30px; font-size: 17px; }
      li::before { inset-block-start: 14px; }
    }
  `,
})
export class RequestJourney {
  readonly status = input<string | null>(null);
  /** טקסט ההסבר מנקודת מבט של משקיע או סוכן */
  readonly view = input<'investor' | 'agent'>('investor');

  protected readonly steps = JOURNEY_STEPS;
  protected readonly current = computed(() => journeyIndex(this.status()));
  protected readonly stopped = computed(() => ['FAILED', 'CANCELLED'].includes(this.status() ?? ''));
  protected readonly label = computed(() => STATUS_LABELS[this.status() ?? 'NO_REQUEST'] ?? this.status() ?? '');
  protected readonly help = computed(() => STATUS_HELP[this.status() ?? 'NO_REQUEST'] ?? null);
}
