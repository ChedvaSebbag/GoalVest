import { Component, computed, input } from '@angular/core';
import { STATUS_LABELS } from '../core/investor/investor.models';

@Component({
  selector: 'gv-status-chip',
  template: `<span class="chip" [attr.data-status]="status()">{{ label() }}</span>`,
  styles: `
    .chip {
      display: inline-block;
      padding: 2px calc(var(--gv-space) * 1.5);
      border-radius: 999px;
      background: color-mix(in srgb, var(--gv-status-submitted) 16%, white);
      color: var(--gv-status-submitted);
      font-size: 0.85rem;
    }
    .chip[data-status='AI_PROCESSING'] {
      background: color-mix(in srgb, var(--gv-status-processing) 16%, white);
      color: var(--gv-status-processing);
    }
    .chip[data-status='AI_EVALUATED'] {
      background: color-mix(in srgb, var(--gv-status-evaluated) 16%, white);
      color: var(--gv-status-evaluated);
    }
    .chip[data-status='IN_REVIEW'] {
      background: color-mix(in srgb, var(--gv-status-review) 16%, white);
      color: var(--gv-status-review);
    }
    .chip[data-status='REEVALUATION_REQUESTED'] {
      background: color-mix(in srgb, var(--gv-status-processing) 16%, white);
      color: var(--gv-status-processing);
    }
    .chip[data-status='OFFER_SENT'],
    .chip[data-status='SENT'] {
      background: color-mix(in srgb, var(--gv-status-offer) 16%, white);
      color: var(--gv-status-offer);
    }
    .chip[data-status='ACCEPTED'] {
      background: color-mix(in srgb, var(--gv-status-accepted) 16%, white);
      color: var(--gv-status-accepted);
    }
    .chip[data-status='DECLINED'],
    .chip[data-status='CANCELLED'],
    .chip[data-status='FAILED'],
    .chip[data-status='INDEX_FAILED'],
    .chip[data-status='INACTIVE'] {
      background: color-mix(in srgb, var(--gv-status-cancelled) 16%, white);
      color: var(--gv-status-cancelled);
    }
    .chip[data-status='PENDING_INDEX'] {
      background: color-mix(in srgb, var(--gv-status-review) 16%, white);
      color: var(--gv-status-review);
    }
    .chip[data-status='INDEXED'],
    .chip[data-status='ACTIVE'] {
      background: color-mix(in srgb, var(--gv-status-accepted) 16%, white);
      color: var(--gv-status-accepted);
    }
  `,
})
export class StatusChip {
  readonly status = input.required<string>();
  protected readonly label = computed(() => STATUS_LABELS[this.status()] ?? this.status());
}
