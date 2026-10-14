import { Pipe, PipeTransform } from '@angular/core';

/** ₪ 1,234. הסכום מגיע כמחרוזת עשרונית מהשרת. */
@Pipe({ name: 'money' })
export class MoneyPipe implements PipeTransform {
  transform(value: string | number | null | undefined): string {
    if (value === null || value === undefined || value === '') {
      return '';
    }
    const amount = Number(value);
    if (Number.isNaN(amount)) {
      return '';
    }
    const formatted = new Intl.NumberFormat('he-IL', { maximumFractionDigits: 0 }).format(Math.round(amount));
    return `₪ ${formatted}`;
  }
}
