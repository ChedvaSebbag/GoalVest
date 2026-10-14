import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { InvestorCommandsService } from '../../../core/investor/investor-commands.service';
import { InvestorQueriesService } from '../../../core/investor/investor-queries.service';
import {
  INCOME_RANGES,
  PRODUCTS,
  QUIZ,
  RISK_COPY,
  QuizQuestion,
  apiErrorMessage,
} from '../../../core/investor/investor.models';
import { Disclaimer } from '../../../shared/disclaimer';

@Component({
  selector: 'gv-risk-quiz',
  imports: [FormsModule, MatButtonModule, MatProgressBarModule, RouterLink, Disclaimer],
  templateUrl: './risk-quiz.html',
  styleUrl: './risk-quiz.scss',
})
export class RiskQuiz {
  private readonly commands = inject(InvestorCommandsService);
  private readonly queries = inject(InvestorQueriesService);

  protected readonly questions = QUIZ;
  protected readonly incomeRanges = INCOME_RANGES;
  protected readonly products = PRODUCTS;
  protected readonly index = signal(0);
  protected readonly answers = signal<Record<string, string | number | string[]>>({});
  protected readonly result = signal<{ label: string; lines: [string, string] } | null>(null);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly birthYear = signal<number | null>(null);
  protected readonly income = signal('');
  protected readonly selectedProducts = signal<string[]>([]);

  protected question(): QuizQuestion {
    return this.questions[this.index()];
  }

  protected progress(): number {
    return this.result() ? 100 : Math.round((this.index() / this.questions.length) * 100);
  }

  protected selected(key: string): string | number | string[] | undefined {
    return this.answers()[key];
  }

  protected choose(key: string, value: string): void {
    this.answers.update((current) => ({ ...current, [key]: value }));
    this.error.set('');
  }

  protected canContinue(): boolean {
    const question = this.question();
    if (question.kind === 'year') {
      return this.yearOk(this.birthYear());
    }
    if (question.kind === 'closing') {
      return this.income() !== '' && this.selectedProducts().length > 0;
    }
    return this.answers()[question.key] != null;
  }

  protected back(): void {
    this.result.set(null);
    this.index.update((value) => Math.max(0, value - 1));
  }

  protected next(): void {
    if (!this.canContinue()) {
      return;
    }
    if (this.index() < this.questions.length - 1) {
      this.index.update((value) => value + 1);
      return;
    }
    this.submit();
  }

  protected toggleProduct(value: string): void {
    this.selectedProducts.update((current) => {
      if (value === 'NONE') {
        return current.includes('NONE') ? [] : ['NONE'];
      }
      const withoutNone = current.filter((item) => item !== 'NONE');
      return withoutNone.includes(value)
        ? withoutNone.filter((item) => item !== value)
        : [...withoutNone, value];
    });
  }

  protected setYear(value: number | string | null): void {
    const year = typeof value === 'string' ? Number(value) : value;
    this.birthYear.set(year != null && !Number.isNaN(year) ? year : null);
  }

  protected productOn(value: string): boolean {
    return this.selectedProducts().includes(value);
  }

  protected restart(): void {
    this.result.set(null);
    this.index.set(0);
    this.error.set('');
  }

  private submit(): void {
    this.saving.set(true);
    this.error.set('');
    const answers = {
      ...this.answers(),
      birthYear: this.birthYear(),
      monthlyIncomeRange: this.income(),
      existingProducts: this.selectedProducts(),
    };
    this.commands.assess(answers).subscribe({
      next: () => {
        this.queries.profile().subscribe({
          next: (profile) => {
            this.saving.set(false);
            const label = profile.riskLabel ?? '';
            this.result.set({
              label,
              lines: RISK_COPY[label] ?? ['הפרופיל נשמר.', 'אפשר להמשיך להגדרת יעד.'],
            });
          },
          error: (error: unknown) => {
            this.saving.set(false);
            this.error.set(apiErrorMessage(error));
          },
        });
      },
      error: (error: unknown) => {
        this.saving.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }

  private yearOk(year: number | null): boolean {
    if (year == null || !Number.isInteger(year)) {
      return false;
    }
    const age = new Date().getFullYear() - year;
    return age >= 18 && age <= 100;
  }
}
