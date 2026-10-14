import { HttpErrorResponse } from '@angular/common/http';

export interface ProductSummary {
  productId: string;
  type: string;
  name: string;
  institutionId: string;
  institutionName: string;
  track: string;
  symbol: string | null;
  feeDeposit: string;
  feeAssets: string;
  return1y: string;
  return3y: string;
  return5y: string;
  stdDev: string;
  riskLevel: number;
  liquidity: string;
  minDeposit: string;
  isActive: boolean;
  documents?: ProductDocument[];
}

export interface ProductDocument {
  documentId: string;
  fileName: string;
  docType: string;
  indexStatus: string;
  chunksCount: number | null;
}

export interface ProductAgent {
  id: string;
  fullName: string;
}

export interface ProductDetails extends ProductSummary {
  description: string;
  liquidityTerms: string;
  taxNotes: string;
  documents: ProductDocument[];
  agents: ProductAgent[];
  fit: null;
}

export interface ProductPage {
  items: ProductSummary[];
  page: number;
  pageSize: number;
  total: number;
}

export interface ProductWrite {
  type: string;
  name: string;
  track: string;
  symbol: string | null;
  feeDeposit: string;
  feeAssets: string;
  return1y: string;
  return3y: string;
  return5y: string;
  stdDev: string;
  riskLevel: number;
  liquidity: string;
  liquidityTerms: string;
  taxNotes: string;
  minDeposit: string;
  description: string;
}

export interface ProductQuery {
  q?: string;
  types?: string[];
  riskMin?: number | null;
  riskMax?: number | null;
  maxFee?: string;
  minReturn3y?: string;
  liquidity?: string;
  institutionId?: string;
  page?: number;
  sort?: string;
  includeInactive?: boolean;
}

export const CHANNELS: { id: string; label: string }[] = [
  { id: 'CAPITAL_MARKET', label: 'שוק ההון' },
  { id: 'HISHTALMUT', label: 'קרן השתלמות' },
  { id: 'GEMEL_POLICY', label: 'גמל ופוליסה' },
];

export const PRODUCT_TYPES: { id: string; label: string }[] = [
  { id: 'HISHTALMUT', label: 'קרן השתלמות' },
  { id: 'GEMEL_INVESTMENT', label: 'גמל להשקעה' },
  { id: 'SAVINGS_POLICY', label: 'פוליסת חיסכון' },
  { id: 'STOCK', label: 'מניה' },
  { id: 'ETF', label: 'תעודת סל' },
];

export const LIQUIDITY_OPTIONS: { id: string; label: string }[] = [
  { id: 'HIGH', label: 'גבוהה' },
  { id: 'PARTIAL', label: 'חלקית' },
  { id: 'NONE', label: 'נמוכה' },
];

export const DOC_TYPES: { id: string; label: string }[] = [
  { id: 'POLICY_TERMS', label: 'תנאי פוליסה' },
  { id: 'QUARTERLY_REPORT', label: 'דוח רבעוני' },
  { id: 'TAX_RULES', label: 'כללי מס' },
  { id: 'MARKET_REPORT', label: 'דוח שוק' },
];

const RISK_LABELS = ['', 'נמוך מאוד', 'נמוך', 'נמוך-בינוני', 'בינוני', 'בינוני-גבוה', 'גבוה', 'גבוה מאוד'];

export function productTypeLabel(type: string): string {
  return PRODUCT_TYPES.find((item) => item.id === type)?.label ?? type;
}

export function liquidityLabel(value: string): string {
  return LIQUIDITY_OPTIONS.find((item) => item.id === value)?.label ?? value;
}

export function docTypeLabel(value: string): string {
  return DOC_TYPES.find((item) => item.id === value)?.label ?? value;
}

export function riskLabel(level: number): string {
  return RISK_LABELS[level] ?? String(level);
}

export function formatPercent(value: string | number | null | undefined, signed = false): string {
  if (value === null || value === undefined || value === '') {
    return '';
  }
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return '';
  }
  const text = `${amount.toFixed(1)}%`;
  return signed && amount > 0 ? `+${text}` : text;
}

export function isMarketType(type: string): boolean {
  return type === 'STOCK' || type === 'ETF';
}

export function apiError(error: unknown): { message: string; fields: Record<string, string> } {
  if (error instanceof HttpErrorResponse && error.error?.error) {
    const body = error.error.error as { message?: string; fields?: Record<string, string> };
    return { message: body.message ?? 'הפעולה נכשלה', fields: body.fields ?? {} };
  }
  return { message: 'הפעולה נכשלה', fields: {} };
}
