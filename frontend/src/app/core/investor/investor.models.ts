import { HttpErrorResponse } from '@angular/common/http';

export interface CommandResult {
  id: string;
  version: number;
}

export interface InvestorProfileView {
  birthYear: number | null;
  maritalStatus: string | null;
  monthlyIncomeRange: string | null;
  hasEmergencyFund: boolean | null;
  existingProducts: string[];
  riskScore: number | null;
  riskLabel: string | null;
}

export interface GoalSummary {
  goalId: string;
  title: string;
  type: string;
  targetAmount: string;
  targetDate: string;
  status: string;
  requestStatus: string | null;
  activeRequestId: string | null;
  consentShareContact: boolean | null;
}

export interface GoalDetails extends GoalSummary {
  initialAmount: string;
  monthlyDeposit: string;
  flexibility: string;
  liquidityNeed: string;
  excludedChannels: string[];
  preferredChannels: string[];
  preferredInstitutions: string[];
}

export interface TimelineItem {
  eventType: string;
  displayText: string;
  actor: string;
  occurredAt: string;
}

export interface GoalWrite {
  type: string;
  title: string;
  initialAmount: string;
  monthlyDeposit: string;
  targetAmount: string;
  targetDate: string;
  flexibility: string;
  liquidityNeed: string;
  excludedChannels: string[];
  preferredChannels: string[];
  preferredInstitutions: string[];
}

export interface InstitutionOption {
  id: string;
  name: string;
}

export const GOAL_TYPES = [
  { value: 'APARTMENT', label: 'דירה', icon: 'home' },
  { value: 'RETIREMENT', label: 'פרישה', icon: 'beach_access' },
  { value: 'CAR', label: 'רכב', icon: 'directions_car' },
  { value: 'EDUCATION', label: 'לימודים', icon: 'school' },
  { value: 'EMERGENCY', label: 'קרן חירום', icon: 'health_and_safety' },
  { value: 'GENERAL', label: 'חיסכון כללי', icon: 'account_balance_wallet' },
] as const;

export const SUGGESTED_TARGET: Record<string, number> = {
  APARTMENT: 400000,
  RETIREMENT: 1000000,
  CAR: 80000,
  EDUCATION: 150000,
  EMERGENCY: 50000,
  GENERAL: 100000,
};

export const FLEXIBILITY = [
  { value: 'FIXED', label: 'התאריך קבוע' },
  { value: 'MONTHS_6', label: 'גמישות של כחצי שנה' },
  { value: 'YEAR_1', label: 'גמישות של כשנה' },
  { value: 'FLEXIBLE', label: 'התאריך גמיש' },
];

export const LIQUIDITY = [
  { value: 'NONE', label: 'אין צורך בנזילות לפני היעד' },
  { value: 'PARTIAL', label: 'ייתכן שאהיה צריך חלק מהכסף' },
  { value: 'HIGH', label: 'חשוב שאוכל למשוך לפני היעד' },
];

export const CHANNELS = [
  { value: 'CAPITAL_MARKET', label: 'שוק ההון' },
  { value: 'HISHTALMUT', label: 'קרן השתלמות' },
  { value: 'GEMEL_POLICY', label: 'גמל ופוליסה' },
];

export const STATUS_LABELS: Record<string, string> = {
  SUBMITTED: 'הוגשה',
  AI_PROCESSING: 'בעיבוד',
  AI_EVALUATED: 'הוערכה',
  IN_REVIEW: 'בבדיקת סוכן',
  OFFER_SENT: 'נשלחה הצעה',
  ACCEPTED: 'התקבלה',
  CANCELLED: 'בוטלה',
  FAILED: 'נכשלה',
  NO_REQUEST: 'ללא בקשה',
  ARCHIVED: 'בארכיון',
  PENDING_INDEX: 'ממתין',
  INDEXED: 'מוטמע',
  INDEX_FAILED: 'נכשל',
  ACTIVE: 'פעיל',
  INACTIVE: 'מושבת',
};

export const CANCELLABLE = new Set(['SUBMITTED', 'AI_EVALUATED', 'IN_REVIEW']);

export const RISK_COPY: Record<string, [string, string]> = {
  'סולידי': ['הפרופיל מעדיף יציבות על פני תנודתיות.', 'כדאי לשקול אפיקים סולידיים יותר, לפי טווח היעד.'],
  'סולידי-מאוזן': ['הפרופיל נוטה ליציבות, עם מקום מוגבל לתנודתיות.', 'כדאי לשקול שילוב זהיר של אפיקים.'],
  'מאוזן': ['הפרופיל משלב יציבות וצמיחה.', 'כדאי לשקול פיזור בין אפיקים, לפי מועד היעד.'],
  'מאוזן-צמיחה': ['הפרופיל מוכן ליותר תנודתיות בטווח ארוך יותר.', 'כדאי לשקול אפיקי צמיחה בחלק מהחיסכון.'],
  'צמיחה': ['הפרופיל מוכן לתנודתיות גבוהה יותר.', 'כדאי לשקול אפיקי צמיחה, כל עוד הטווח מתאים.'],
};

export interface QuizOption {
  value: string;
  label: string;
}

export interface QuizQuestion {
  key: string;
  title: string;
  kind: 'year' | 'single' | 'closing';
  options?: QuizOption[];
}

export const QUIZ: QuizQuestion[] = [
  { key: 'birthYear', title: 'באיזו שנה נולדת?', kind: 'year' },
  {
    key: 'horizon',
    title: 'לכמה זמן הכסף יכול להישאר מושקע?',
    kind: 'single',
    options: [
      { value: 'UNDER_3', label: 'פחות מ-3 שנים' },
      { value: 'Y3_TO_5', label: '3 עד 5 שנים' },
      { value: 'Y6_TO_10', label: '6 עד 10 שנים' },
      { value: 'Y11_TO_20', label: '11 עד 20 שנים' },
      { value: 'OVER_20', label: 'יותר מ-20 שנה' },
    ],
  },
  {
    key: 'dropReaction',
    title: 'איך תגיב/י לירידה של 20% בשווי ההשקעה?',
    kind: 'single',
    options: [
      { value: 'SELL_ALL', label: 'אמכור את הכול' },
      { value: 'SELL_SOME', label: 'אמכור חלק' },
      { value: 'WAIT', label: 'אמתין' },
      { value: 'HOLD', label: 'אמשיך כרגיל' },
      { value: 'BUY_MORE', label: 'אגדיל את ההשקעה' },
    ],
  },
  {
    key: 'experience',
    title: 'מה הניסיון שלך בהשקעות?',
    kind: 'single',
    options: [
      { value: 'NONE', label: 'אין ניסיון' },
      { value: 'DEPOSITS', label: 'פיקדונות בלבד' },
      { value: 'FUNDS', label: 'קרנות' },
      { value: 'OCCASIONAL_STOCKS', label: 'מניות מדי פעם' },
      { value: 'ACTIVE', label: 'ניהול תיק פעיל' },
    ],
  },
  {
    key: 'incomeStability',
    title: 'כמה ההכנסה שלך יציבה?',
    kind: 'single',
    options: [
      { value: 'UNSTABLE', label: 'לא יציבה' },
      { value: 'VARIABLE', label: 'משתנה' },
      { value: 'MOSTLY_STABLE', label: 'יציבה ברובה' },
      { value: 'SALARIED', label: 'הכנסה קבועה' },
      { value: 'SURPLUS', label: 'קבועה, עם עודף' },
    ],
  },
  {
    key: 'emergencyFund',
    title: 'האם יש קרן חירום?',
    kind: 'single',
    options: [
      { value: 'NONE', label: 'אין' },
      { value: 'PARTIAL', label: 'כיסוי חלקי' },
      { value: 'YES', label: 'כן, כיסוי מלא' },
    ],
  },
  {
    key: 'maritalStatus',
    title: 'מצב משפחתי',
    kind: 'single',
    options: [
      { value: 'SINGLE', label: 'רווק/ה' },
      { value: 'MARRIED', label: 'נשוי/אה' },
      { value: 'DIVORCED', label: 'גרוש/ה' },
      { value: 'WIDOWED', label: 'אלמן/ה' },
    ],
  },
  { key: 'closing', title: 'הכנסה ומוצרים שכבר יש לך', kind: 'closing' },
];

export const INCOME_RANGES: QuizOption[] = [
  { value: 'UP_TO_10K', label: 'עד 10,000 ₪' },
  { value: 'FROM_10K_TO_20K', label: '10,000–20,000 ₪' },
  { value: 'FROM_20K_TO_35K', label: '20,000–35,000 ₪' },
  { value: 'FROM_35K_TO_50K', label: '35,000–50,000 ₪' },
  { value: 'OVER_50K', label: 'מעל 50,000 ₪' },
];

export const PRODUCTS: QuizOption[] = [
  { value: 'HISHTALMUT', label: 'קרן השתלמות' },
  { value: 'GEMEL', label: 'קופת גמל' },
  { value: 'POLICY', label: 'פוליסת חיסכון' },
  { value: 'PENSION', label: 'קרן פנסיה' },
  { value: 'NONE', label: 'אין' },
];

export function goalTypeLabel(type: string): string {
  return GOAL_TYPES.find((item) => item.value === type)?.label ?? type;
}

export function optionLabel(options: { value: string; label: string }[], value: string): string {
  return options.find((item) => item.value === value)?.label ?? value;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) {
    return '';
  }
  const [year, month, day] = iso.slice(0, 10).split('-');
  return `${day}/${month}/${year}`;
}

export function apiErrorMessage(error: unknown, fallback = 'משהו השתבש. נסו שוב.'): string {
  if (error instanceof HttpErrorResponse) {
    const message = error.error?.error?.message;
    if (typeof message === 'string' && message) {
      return message;
    }
  }
  return fallback;
}

export function addMonthsIso(months: number): string {
  const copy = new Date();
  copy.setMonth(copy.getMonth() + months);
  const month = String(copy.getMonth() + 1).padStart(2, '0');
  const day = String(copy.getDate()).padStart(2, '0');
  return `${copy.getFullYear()}-${month}-${day}`;
}
