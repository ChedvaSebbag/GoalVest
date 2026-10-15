import { Component, input } from '@angular/core';
import {
  AssessmentView,
  ChannelFigures,
} from '../../../core/investor/investor.models';
import { Disclaimer } from '../../../shared/disclaimer';
import { InfoTip } from '../../../shared/info-tip';

@Component({
  selector: 'gv-assessment-card',
  imports: [Disclaimer, InfoTip],
  templateUrl: './assessment-card.html',
  styleUrl: './assessment-card.scss',
})
export class AssessmentCard {
  readonly assessment = input.required<AssessmentView>();

  /** משפט אחד שמסביר מה הציון הכללי אומר */
  protected verdict(): string {
    const score = this.assessment().overallScore;
    if (score >= 70) return 'התאמה גבוהה: יש אפיקים שמתאימים היטב ליעד, לטווח ולפרופיל הסיכון שלך.';
    if (score >= 40) return 'התאמה בינונית: יש אפשרויות מתאימות, אבל כדאי לקרוא את דגלי הסיכון ואת הנימוק.';
    return 'התאמה נמוכה: ייתכן שהסכום, הטווח או ההעדפות קשים להשגה. כדאי לשקול לשנות את היעד או להתייעץ עם סוכן.';
  }

  protected readonly channels: { key: keyof ChannelFigures; label: string }[] = [
    { key: 'capitalMarket', label: 'שוק ההון' },
    { key: 'hishtalmut', label: 'קרן השתלמות' },
    { key: 'gemelPolicy', label: 'גמל ופוליסה' },
  ];

  protected score(key: keyof ChannelFigures): number {
    return this.assessment().channelScores[key] ?? 0;
  }

  protected share(key: keyof ChannelFigures): string {
    return Number(this.assessment().allocation[key] ?? 0).toFixed(1);
  }

  protected severity(value: string): string {
    const labels: Record<string, string> = { high: 'חמור', medium: 'בינוני', info: 'מידע' };
    return labels[value] ?? value;
  }

  protected sourceKind(value: string): string {
    const labels: Record<string, string> = { rag: 'מסמך', web: 'אתר', tool: 'כלי' };
    return labels[value] ?? value;
  }
}
