import { Component, computed, input } from '@angular/core';
import { MatTooltipModule } from '@angular/material/tooltip';
import { GLOSSARY } from '../core/help/help-content';

/** סימן ? קטן ליד מונח מקצועי. מעבר עכבר או לחיצה (גם בטלפון) מציגים הסבר מהמילון. */
@Component({
  selector: 'gv-info-tip',
  imports: [MatTooltipModule],
  template: `
    @if (entry(); as item) {
      <button
        type="button"
        class="tip"
        #tip="matTooltip"
        [matTooltip]="item.text"
        matTooltipPosition="above"
        matTooltipClass="gv-tooltip"
        [attr.aria-label]="'מה זה ' + item.term + '? ' + item.text"
        (click)="tip.toggle(); $event.stopPropagation()"
      >
        <span class="material-symbols-rounded" aria-hidden="true">help</span>
      </button>
    }
  `,
  styles: `
    :host { display: inline-flex; vertical-align: middle; }
    .tip {
      display: inline-grid;
      place-items: center;
      inline-size: 20px;
      block-size: 20px;
      padding: 0;
      margin-inline-start: 4px;
      border: 0;
      border-radius: 50%;
      background: transparent;
      color: var(--gv-text-muted);
      cursor: help;
    }
    .tip:hover, .tip:focus-visible { color: var(--gv-primary); background: var(--gv-bg); }
    .material-symbols-rounded { font-size: 18px; }
  `,
})
export class InfoTip {
  readonly term = input.required<string>();
  protected readonly entry = computed(() => GLOSSARY[this.term()] ?? null);
}
