export type UserRole = 'INVESTOR' | 'AGENT';

export interface SessionUser {
  id: string;
  role: UserRole;
  fullName: string;
}

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  user: SessionUser;
}

export interface RegisteredUser {
  id: string;
  version: number;
}

export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  phone: string;
  role: UserRole;
  institutionId: string | null;
  status: string;
}

export interface Institution {
  id: string;
  name: string;
}

export interface RegisterPayload {
  fullName: string;
  email: string;
  phone: string;
  password: string;
  role: UserRole;
  institutionId?: string;
  licenseNo?: string;
}

export function homeRouteForRole(role: UserRole): string {
  return role === 'AGENT' ? '/agent' : '/investor';
}
