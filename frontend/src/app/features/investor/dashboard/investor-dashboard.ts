import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { chartColor } from '../../../core/charts';
import { InvestorQueriesService } from '../../../core/investor/investor-queries.service';
import {
  InvestorDashboard as DashboardView,
  InvestorDashboardGoal,
  formatDate,
  goalTypeLabel,
} from '../../../core/investor/investor.models';
import { Disclaimer } from '../../../shared/disclaimer';
import { MoneyPipe } from '../../../shared/money.pipe';
import { StatusChip } from '../../../shared/status-chip';
import { InfoTip } from '../../../shared/info-tip';
import { NextStep, NextStepCard } from '../../../shared/next-step';

@Component({
  selector: 'gv-investor-dashboard',
  imports: [FormsModule, RouterLink, MatButtonModule, BaseChartDirective, Disclaimer, MoneyPipe, StatusChip, InfoTip, NextStepCard],
  templateUrl: './investor-dashboard.html',
  styleUrl: './investor-dashboard.scss',
})
export class InvestorDashboard {
  private readonly queries = inject(InvestorQueriesService);
  private readonly router = inject(Router);

  protected readonly formatDate = formatDate;
  protected readonly goalTypeLabel = goalTypeLabel;
  protected readonly dashboard = signal<DashboardView | null>(null);
  protected readonly failed = signal(false);
  protected readonly selectedId = signal<string | null>(null);
  protected query = '';

  protected readonly selected = computed(() => {
    const goals = this.dashboard()?.goals ?? [];
    return goals.find((goal) => goal.goalId === this.selectedId()) ?? goals[0] ?? null;
  });

  /** מה המשקיע צריך לעשות עכשיו, לפי מצב היעדים והבקשות */
  protected readonly nextStep = computed<NextStep | null>(() => {
    const view = this.dashboard();
    if (view === null || this.failed()) {
      return null;
    }
    const goals = view.goals;
    const withStatus = (...statuses: (string | null)[]) => goals.find((goal) => statuses.includes(goal.requestStatus));
    if (goals.length === 0) {
      return {
        icon: 'flag',
        title: 'להגדיר את היעד הראשון',
        text: 'מה המטרה? דירה, לימודים, פרישה או רכב. האשף לוקח בערך שתי דקות, ובסוף היעד נשלח להערכת AI.',
        cta: { label: 'יעד חדש', link: '/investor/goals/new' },
      };
    }
    if (view.pendingOffers > 0) {
      return {
        icon: 'mark_email_unread',
        tone: 'success',
        title: view.pendingOffers === 1 ? 'יש לך הצעה שממתינה לתשובה' : `יש לך ${view.pendingOffers} הצעות שממתינות לתשובה`,
        text: 'סוכן שלח הצעה מותאמת ליעד שלך. אפשר לעבור על המוצרים והאחוזים ולאשר או לדחות.',
        cta: { label: 'להצעות', link: '/investor/offers' },
      };
    }
    const failed = withStatus('FAILED');
    if (failed) {
      return {
        icon: 'replay',
        tone: 'warning',
        title: `ההערכה של "${failed.title}" לא הושלמה`,
        text: 'אפשר לנסות שוב: נכנסים לעריכת היעד ושומרים, והבקשה נשלחת מחדש.',
        cta: { label: 'עריכה ושליחה מחדש', link: ['/investor/goals', failed.goalId, 'edit'] },
      };
    }
    const evaluated = withStatus('AI_EVALUATED');
    if (evaluated) {
      return {
        icon: 'insights',
        tone: 'success',
        title: `ההערכה של "${evaluated.title}" מוכנה`,
        text: 'אפשר לקרוא את הציון, התמהיל המומלץ והנימוק. בינתיים סוכן מהגופים המתאימים ייקח את הבקשה לטיפול.',
        cta: { label: 'לצפייה בהערכה', link: ['/investor/goals', evaluated.goalId] },
      };
    }
    const processing = withStatus('SUBMITTED', 'AI_PROCESSING', 'REEVALUATION_REQUESTED');
    if (processing) {
      return {
        icon: 'smart_toy',
        title: `סוכן ה-AI בודק את "${processing.title}"`,
        text: 'זה לוקח בדרך כלל דקה עד שלוש. אין צורך לרענן, הסטטוס מתעדכן לבד.',
        cta: { label: 'למעקב', link: ['/investor/goals', processing.goalId] },
      };
    }
    const review = withStatus('IN_REVIEW');
    if (review) {
      return {
        icon: 'support_agent',
        title: 'סוכן בודק את הבקשה שלך',
        text: `הבקשה של "${review.title}" בטיפול סוכן. כשתישלח הצעה תופיע התראה בפעמון.`,
        cta: { label: 'לפרטי היעד', link: ['/investor/goals', review.goalId] },
      };
    }
    const draft = withStatus(null, 'NO_REQUEST', 'CANCELLED');
    if (draft) {
      return {
        icon: 'send',
        title: `"${draft.title}" עוד לא נשלח להערכה`,
        text: 'כדי לקבל הערכה והצעות, פותחים את עריכת היעד, מסמנים את ההסכמות ושומרים.',
        cta: { label: 'שליחה להערכה', link: ['/investor/goals', draft.goalId, 'edit'] },
      };
    }
    return {
      icon: 'celebration',
      tone: 'success',
      title: 'הכול מעודכן',
      text: 'אין פעולות פתוחות. אפשר להוסיף יעד נוסף או להשוות מוצרים בקטלוג.',
      cta: { label: 'יעד נוסף', link: '/investor/goals/new' },
    };
  });

  protected readonly donut = computed<ChartData<'doughnut'>>(() => {
    const allocation = this.selected()?.assessment?.allocation;
    return {
      labels: ['שוק ההון', 'קרן השתלמות', 'גמל ופוליסה'],
      datasets: [{
        data: [
          allocation?.capitalMarket ?? 0,
          allocation?.hishtalmut ?? 0,
          allocation?.gemelPolicy ?? 0,
        ],
        backgroundColor: [
          chartColor('--gv-primary'),
          chartColor('--gv-accent'),
          chartColor('--gv-success'),
        ],
      }],
    };
  });

  protected readonly donutOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    plugins: { legend: { rtl: true, labels: { font: { family: 'Heebo' } } } },
  };

  constructor() {
    this.load();
  }

  protected load(): void {
    this.failed.set(false);
    this.dashboard.set(null);
    this.queries.dashboard().subscribe({
      next: (dashboard) => {
        this.dashboard.set(dashboard);
        this.selectedId.set(dashboard.goals[0]?.goalId ?? null);
      },
      error: () => {
        this.dashboard.set({ plannedCapital: '0.00', activeGoals: 0, pendingOffers: 0, goals: [] });
        this.failed.set(true);
      },
    });
  }

  protected choose(goal: InvestorDashboardGoal): void {
    this.selectedId.set(goal.goalId);
  }

  protected search(): void {
    void this.router.navigate(['/products'], { queryParams: { q: this.query.trim() } });
  }

  protected statusOf(goal: InvestorDashboardGoal): string {
    return goal.requestStatus ?? 'NO_REQUEST';
  }
}
