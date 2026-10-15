import { AssessmentView, TimelineItem } from '../investor/investor.models';

export interface AgentDashboard {
  evaluated: number;
  inReview: number;
  offerSent: number;
  offersSent: number;
  offersAccepted: number;
  conversionRate: string | null;
  averageScore: string | null;
}

export interface ProductInterest {
  productId: string;
  name: string;
  recommended: number;
  offers: number;
  accepted: number;
}

export interface LeadSummary {
  requestId: string;
  investorName: string;
  goalTitle: string;
  goalType: string;
  amount: string;
  horizonYears: number;
  riskLabel: string;
  aiScore: number | null;
  status: string;
  createdAt: string;
  isNew: boolean;
}

export interface LeadPage {
  items: LeadSummary[];
  page: number;
  pageSize: number;
  total: number;
}

export interface LeadInvestor {
  displayName: string;
  email: string | null;
  phone: string | null;
}

export interface LeadGoal {
  title: string;
  type: string;
  targetAmount: string;
  initialAmount: string;
  monthlyDeposit: string;
  targetDate: string;
  horizonYears: number;
  riskLabel: string;
  riskScore: number | null;
  liquidityNeed: string | null;
}

export interface LeadProductOption {
  productId: string;
  name: string;
}

export interface LeadDetails {
  requestId: string;
  status: string;
  claimedByMe: boolean;
  investor: LeadInvestor;
  goal: LeadGoal;
  aiScore: number | null;
  review: { status: string | null; note: string | null };
  assessment: AssessmentView | null;
  timeline: TimelineItem[];
  products: LeadProductOption[];
  createdAt: string;
}

export interface OfferDraftItem {
  productId: string;
  percent: number | null;
}
