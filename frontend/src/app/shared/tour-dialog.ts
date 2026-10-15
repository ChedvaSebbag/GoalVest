import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { GuideStep } from '../core/help/help-content';

export interface TourDialogData {
  steps: GuideStep[];
}

@Component({
  selector: 'gv-tour-dialog',
  imports: [MatDialogModule, MatButtonModule, RouterLink],
  template: `
    <div class="tour" (keydown.arrowLeft)="next()" (keydown.arrowRight)="back()">
      <span class="icon material-symbols-rounded" aria-hidden="true">{{ step().icon }}</span>
      <h2 mat-dialog-title>{{ step().title }}</h2>
      <mat-dialog-content>
        <p aria-live="polite">{{ step().text }}</p>
      </mat-dialog-content>
      <div class="dots" role="tablist" aria-label="שלבי הסיור">
        @for (item of data.steps; track item.title; let i = $index) {
          <button
            type="button"
            role="tab"
            [class.on]="i === index()"
            [attr.aria-selected]="i === index()"
            [attr.aria-label]="'שלב ' + (i + 1) + ' מתוך ' + data.steps.length"
            (click)="index.set(i)"
          ></button>
        }
      </div>
      <mat-dialog-actions>
        @if (!last()) {
          <button type="button" mat-button (click)="close()">דלג על הסיור</button>
        }
        <span class="spacer"></span>
        @if (index() > 0) {
          <button type="button" mat-stroked-button (click)="back()">הקודם</button>
        }
        @if (!last()) {
          <button type="button" mat-flat-button (click)="next()">הבא</button>
        } @else {
          <a mat-stroked-button routerLink="/help" (click)="close()">למדריך המלא</a>
          <button type="button" mat-flat-button (click)="close()">בואו נתחיל</button>
        }
      </mat-dialog-actions>
    </div>
  `,
  styles: `
    .tour { padding-block-start: calc(var(--gv-space) * 3); text-align: center; }
    .icon {
      font-size: 56px;
      color: var(--gv-primary);
      background: color-mix(in srgb, var(--gv-primary) 10%, var(--gv-surface));
      border-radius: 50%;
      padding: calc(var(--gv-space) * 2);
    }
    h2 { color: var(--gv-primary); }
    p { font-size: 1.05rem; line-height: 1.7; margin: 0; color: var(--gv-text); }
    .dots { display: flex; justify-content: center; gap: 6px; margin-block: calc(var(--gv-space) * 2); }
    .dots button {
      inline-size: 8px;
      block-size: 8px;
      padding: 0;
      border: 0;
      border-radius: 999px;
      background: var(--gv-skeleton);
      cursor: pointer;
      transition: inline-size 0.2s;
    }
    .dots button.on { inline-size: 24px; background: var(--gv-primary); }
    .spacer { flex: 1; }
    mat-dialog-actions { gap: var(--gv-space); }
  `,
})
export class TourDialog {
  protected readonly data = inject<TourDialogData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<TourDialog>);
  protected readonly index = signal(0);
  protected readonly step = computed(() => this.data.steps[this.index()]);
  protected readonly last = computed(() => this.index() === this.data.steps.length - 1);

  protected next(): void {
    this.index.update((i) => Math.min(i + 1, this.data.steps.length - 1));
  }

  protected back(): void {
    this.index.update((i) => Math.max(i - 1, 0));
  }

  protected close(): void {
    this.ref.close();
  }
}
