import { Component, computed, inject, isDevMode, signal } from '@angular/core';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../core/auth/auth.service';
import { AuthQueriesService } from '../../core/auth/auth-queries.service';
import { Institution, UserRole, homeRouteForRole } from '../../core/auth/auth.models';

@Component({
  selector: 'gv-auth-page',
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatAutocompleteModule,
    MatProgressBarModule,
  ],
  templateUrl: './auth-page.html',
  styleUrl: './auth-page.scss',
})
export class AuthPage {
  private readonly auth = inject(AuthService);
  private readonly institutionsQuery = inject(AuthQueriesService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly tabIndex = signal(0);
  protected readonly role = signal<UserRole>('INVESTOR');
  protected readonly showLoginPassword = signal(false);
  protected readonly showRegisterPassword = signal(false);
  protected readonly submitting = signal(false);
  protected readonly loginError = signal('');
  protected readonly registerError = signal('');
  protected readonly justRegistered = signal(false);
  protected readonly institutionsState = signal<'loading' | 'ready' | 'error'>('loading');
  protected readonly institutions = signal<Institution[]>([]);
  protected readonly institutionFilter = signal('');
  protected readonly selectedInstitutionId = signal<string | null>(null);

  protected readonly filteredInstitutions = computed(() => {
    const query = this.institutionFilter().trim();
    const all = this.institutions();
    if (!query || all.some((item) => item.id === query)) {
      return all;
    }
    return all.filter((item) => item.name.includes(query));
  });

  /** חשבונות ה-seed מוצגים רק בפיתוח ורק על המחשב המקומי – לא בקישור שיתוף ולא ב-production */
  protected readonly showDemo =
    isDevMode() && ['localhost', '127.0.0.1'].includes(globalThis.location?.hostname ?? '');
  protected readonly demoAccounts = [
    { label: 'משקיעה לדוגמה', email: 'demo.investor1@goalvest.test' },
    { label: 'סוכן – הראל', email: 'demo.agent.harel@goalvest.test' },
    { label: 'סוכן – כלל', email: 'demo.agent.clal@goalvest.test' },
    { label: 'סוכן – מגדל', email: 'demo.agent.migdal@goalvest.test' },
  ];

  protected fillDemo(email: string): void {
    this.loginForm.setValue({ email, password: 'Demo1234' });
  }

  protected readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  protected readonly institutionSearch = new FormControl('', { nonNullable: true });

  protected readonly registerForm = this.formBuilder.nonNullable.group({
    fullName: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    phone: ['', [Validators.required, Validators.minLength(9)]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    licenseNo: [''],
  });

  constructor() {
    this.route.data.subscribe((data) => {
      this.tabIndex.set(data['tab'] === 'register' ? 1 : 0);
    });
    this.route.queryParamMap.subscribe((params) => {
      this.justRegistered.set(params.get('registered') === '1');
    });
    this.loadInstitutions();
  }

  protected onTab(index: number): void {
    if (index === this.tabIndex()) {
      return;
    }
    void this.router.navigateByUrl(index === 1 ? '/auth/register' : '/auth/login');
  }

  protected selectRole(role: UserRole): void {
    this.role.set(role);
    if (role === 'INVESTOR') {
      this.selectedInstitutionId.set(null);
      this.institutionSearch.setValue('');
      this.registerForm.controls.licenseNo.setValue('');
    }
  }

  protected loadInstitutions(): void {
    this.institutionsState.set('loading');
    this.institutionsQuery.institutions().subscribe({
      next: (items) => {
        this.institutions.set(items);
        this.institutionsState.set('ready');
      },
      error: () => this.institutionsState.set('error'),
    });
  }

  protected onInstitutionInput(value: string): void {
    this.institutionFilter.set(value);
    const match = this.institutions().find((item) => item.name === value);
    this.selectedInstitutionId.set(match?.id ?? null);
  }

  protected onInstitutionSelected(id: string): void {
    this.selectedInstitutionId.set(id);
    this.institutionFilter.set(id);
  }

  protected readonly institutionName = (value: string | null): string => {
    if (!value) {
      return '';
    }
    return this.institutions().find((item) => item.id === value)?.name ?? value;
  };

  protected strengthLabel(): string {
    const password = this.registerForm.controls.password.value;
    let score = 0;
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (/\p{L}/u.test(password) && /\d/.test(password)) score += 1;
    if (/[^\p{L}\d]/u.test(password)) score += 1;
    return ['חלשה', 'בינונית', 'טובה', 'חזקה'][Math.max(score - 1, 0)] ?? 'חלשה';
  }

  protected submitLogin(): void {
    if (this.loginForm.invalid || this.submitting()) {
      this.loginForm.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.loginError.set('');
    const { email, password } = this.loginForm.getRawValue();
    this.auth.login(email, password).subscribe({
      next: (role) => {
        this.submitting.set(false);
        void this.router.navigateByUrl(homeRouteForRole(role));
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        this.loginError.set(messageOf(error, 'אימייל או סיסמה שגויים'));
      },
    });
  }

  protected submitRegister(): void {
    if (this.registerForm.invalid || this.submitting()) {
      this.registerForm.markAllAsTouched();
      return;
    }
    if (this.role() === 'AGENT' && !this.selectedInstitutionId()) {
      this.registerError.set('יש לבחור גוף פיננסי מהרשימה');
      return;
    }
    if (this.role() === 'AGENT' && !this.registerForm.controls.licenseNo.value.trim()) {
      this.registerError.set('יש להזין מספר רישיון');
      return;
    }
    this.submitting.set(true);
    this.registerError.set('');
    const value = this.registerForm.getRawValue();
    this.auth.register({
      fullName: value.fullName,
      email: value.email,
      phone: value.phone,
      password: value.password,
      role: this.role(),
      institutionId: this.role() === 'AGENT' ? this.selectedInstitutionId() ?? undefined : undefined,
      licenseNo: this.role() === 'AGENT' ? value.licenseNo.trim() : undefined,
    }).subscribe({
      next: () => {
        this.submitting.set(false);
        void this.router.navigate(['/auth/login'], { queryParams: { registered: '1' } });
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        this.registerError.set(messageOf(error, 'לא הצלחנו להשלים את ההרשמה'));
      },
    });
  }
}

function messageOf(error: unknown, fallback: string): string {
  if (!(error instanceof HttpErrorResponse)) {
    return fallback;
  }
  if (error.status === 0 || error.status >= 500) {
    return 'לא הצלחנו להשלים את הפעולה. נסו שוב.';
  }
  const message = error.error?.error?.message;
  return typeof message === 'string' && message ? message : fallback;
}
