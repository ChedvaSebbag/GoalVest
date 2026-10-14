import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { InvestorCommandsService } from '../../../core/investor/investor-commands.service';
import { InvestorQueriesService } from '../../../core/investor/investor-queries.service';
import {
  CHANNELS,
  FLEXIBILITY,
  GOAL_TYPES,
  GoalWrite,
  InstitutionOption,
  LIQUIDITY,
  SUGGESTED_TARGET,
  addMonthsIso,
  apiErrorMessage,
} from '../../../core/investor/investor.models';

@Component({
  selector: 'gv-goal-wizard',
  imports: [ReactiveFormsModule, MatButtonModule, RouterLink],
  templateUrl: './goal-wizard.html',
  styleUrl: './goal-wizard.scss',
})
export class GoalWizard {
  private readonly commands = inject(InvestorCommandsService);
  private readonly queries = inject(InvestorQueriesService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly forms = inject(FormBuilder);

  protected readonly types = GOAL_TYPES;
  protected readonly flexibilityOptions = FLEXIBILITY;
  protected readonly liquidityOptions = LIQUIDITY;
  protected readonly channels = CHANNELS;
  protected readonly minDate = addMonthsIso(6);
  protected readonly goalId = this.route.snapshot.paramMap.get('id');
  protected readonly institutions = signal<InstitutionOption[]>([]);
  protected readonly institutionsFailed = signal(false);
  protected readonly requestStatus = signal<string | null>(null);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly step = signal(1);

  protected readonly form = this.forms.nonNullable.group({
    type: ['', Validators.required],
    title: ['', [Validators.required, Validators.minLength(2)]],
    initialAmount: [0, [Validators.required, Validators.min(0)]],
    monthlyDeposit: [0, [Validators.required, Validators.min(0)]],
    targetAmount: [0, [Validators.required, Validators.min(1)]],
    targetDate: ['', Validators.required],
    flexibility: ['', Validators.required],
    liquidityNeed: ['', Validators.required],
    excludedChannels: [[] as string[]],
    preferredChannels: [[] as string[]],
    preferredInstitutions: [[] as string[]],
    consent: [false, Validators.requiredTrue],
    legal: [false, Validators.requiredTrue],
  });

  constructor() {
    this.loadInstitutions();
    if (this.goalId) {
      this.queries.goal(this.goalId).subscribe({
        next: (goal) => {
          this.requestStatus.set(goal.requestStatus);
          this.form.patchValue({
            type: goal.type,
            title: goal.title,
            initialAmount: Number(goal.initialAmount),
            monthlyDeposit: Number(goal.monthlyDeposit),
            targetAmount: Number(goal.targetAmount),
            targetDate: goal.targetDate,
            flexibility: goal.flexibility,
            liquidityNeed: goal.liquidityNeed,
            excludedChannels: goal.excludedChannels,
            preferredChannels: goal.preferredChannels,
            preferredInstitutions: goal.preferredInstitutions,
            consent: goal.consentShareContact === true,
          });
        },
        error: () => this.error.set('לא הצלחנו לטעון את היעד.'),
      });
    }
  }

  protected loadInstitutions(): void {
    this.institutionsFailed.set(false);
    this.queries.institutions().subscribe({
      next: (page) => this.institutions.set(page.items),
      error: () => this.institutionsFailed.set(true),
    });
  }

  protected pickType(type: string): void {
    this.form.controls.type.setValue(type);
    const title = this.form.controls.title;
    const target = this.form.controls.targetAmount;
    if (!title.value) {
      title.setValue(this.types.find((item) => item.value === type)?.label ?? '');
    }
    if (target.pristine || target.value === 0) {
      target.setValue(SUGGESTED_TARGET[type] ?? 0);
    }
  }

  protected toggle(list: 'excludedChannels' | 'preferredChannels', value: string): void {
    const selected = this.form.controls[list];
    const otherName = list === 'excludedChannels' ? 'preferredChannels' : 'excludedChannels';
    const other = this.form.controls[otherName];
    const next = selected.value.includes(value)
      ? selected.value.filter((item) => item !== value)
      : [...selected.value, value];
    selected.setValue(next);
    other.setValue(other.value.filter((item) => item !== value));
  }

  protected on(list: 'excludedChannels' | 'preferredChannels', value: string): boolean {
    return this.form.controls[list].value.includes(value);
  }

  protected toggleInstitution(id: string): void {
    const control = this.form.controls.preferredInstitutions;
    control.setValue(
      control.value.includes(id) ? control.value.filter((item) => item !== id) : [...control.value, id],
    );
  }

  protected readonly savedWithoutRequest = signal<string | null>(null);

  protected stepReady(step: number): boolean {
    const value = this.form.getRawValue();
    if (step === 1) {
      return value.type !== '' && value.title.trim().length >= 2;
    }
    if (step === 2) {
      return value.targetAmount > 0 && (value.initialAmount > 0 || value.monthlyDeposit > 0);
    }
    if (step === 3) {
      return value.targetDate >= this.minDate && value.flexibility !== '';
    }
    return value.liquidityNeed !== '' && value.consent && value.legal && this.requestStatus() !== 'AI_PROCESSING';
  }

  protected go(next: number): void {
    if (next > this.step() && !this.stepReady(this.step())) {
      return;
    }
    this.step.set(next);
  }

  protected save(): void {
    if (!this.stepReady(4) || this.saving()) {
      return;
    }
    this.saving.set(true);
    this.error.set('');
    this.savedWithoutRequest.set(null);
    const body = this.payload();
    if (this.goalId) {
      this.commands.updateGoal(this.goalId, { ...body, consentShareContact: true }).subscribe({
        next: () => void this.router.navigate(['/investor/goals', this.goalId]),
        error: (error: unknown) => this.fail(error),
      });
      return;
    }
    this.commands.createGoal(body).subscribe({
      next: (created) => {
        this.commands.submitRequest(created.id, true).subscribe({
          next: () => void this.router.navigate(['/investor/goals', created.id]),
          error: () => {
            this.saving.set(false);
            this.savedWithoutRequest.set(created.id);
            this.error.set('היעד נשמר, אבל ההגשה להערכה נכשלה.');
          },
        });
      },
      error: (error: unknown) => this.fail(error),
    });
  }

  private payload(): GoalWrite {
    const value = this.form.getRawValue();
    return {
      type: value.type,
      title: value.title.trim(),
      initialAmount: value.initialAmount.toFixed(2),
      monthlyDeposit: value.monthlyDeposit.toFixed(2),
      targetAmount: value.targetAmount.toFixed(2),
      targetDate: value.targetDate,
      flexibility: value.flexibility,
      liquidityNeed: value.liquidityNeed,
      excludedChannels: value.excludedChannels,
      preferredChannels: value.preferredChannels,
      preferredInstitutions: value.preferredInstitutions,
    };
  }

  private fail(error: unknown): void {
    this.saving.set(false);
    this.error.set(apiErrorMessage(error));
  }
}
