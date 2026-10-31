import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTabsModule } from '@angular/material/tabs';
import { AuthService } from '../../core/auth/auth.service';
import { FAQ, GLOSSARY, GUIDES, HelpRole, STATUS_HELP } from '../../core/help/help-content';
import { TourService } from '../../core/help/tour.service';
import { STATUS_LABELS } from '../../core/investor/investor.models';

/** דף עזרה: איך המערכת עובדת, מדריך לכל תפקיד, הסבר סטטוסים, מילון מונחים ושאלות נפוצות. */
@Component({
  selector: 'gv-help-page',
  imports: [RouterLink, MatButtonModule, MatExpansionModule, MatTabsModule],
  templateUrl: './help-page.html',
  styleUrl: './help-page.scss',
})
export class HelpPage {
  private readonly auth = inject(AuthService);
  private readonly tour = inject(TourService);

  protected readonly user = this.auth.user;
  protected readonly guides = GUIDES;
  protected readonly faq = FAQ;
  protected readonly glossary = Object.values(GLOSSARY).sort((a, b) => a.term.localeCompare(b.term, 'he'));
  protected readonly statuses = [
    'NO_REQUEST', 'SUBMITTED', 'AI_PROCESSING', 'AI_EVALUATED', 'IN_REVIEW',
    'REEVALUATION_REQUESTED', 'OFFER_SENT', 'ACCEPTED', 'CANCELLED', 'FAILED',
  ].map((code) => ({ code, label: STATUS_LABELS[code] ?? code, ...STATUS_HELP[code] }));

  protected readonly role = computed<HelpRole | null>(() => {
    const role = this.user()?.role;
    return role === 'INVESTOR' || role === 'AGENT' ? role : null;
  });

  /** לשונית פתיחה לפי התפקיד של המשתמש המחובר */
  protected readonly tab = signal(this.role() === 'AGENT' ? 1 : 0);
  protected readonly filter = signal('');
  protected readonly filteredGlossary = computed(() => {
    const q = this.filter().trim();
    return q ? this.glossary.filter((g) => g.term.includes(q) || g.text.includes(q)) : this.glossary;
  });

  protected canFollow(role: HelpRole): boolean {
    return this.role() === role;
  }

  protected replayTour(): void {
    this.tour.show(this.role());
  }
}
