import { Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { AuthService } from './core/auth/auth.service';
import { homeRouteForRole } from './core/auth/auth.models';
import { TourService } from './core/help/tour.service';
import { NotificationBell } from './shell/notification-bell';

interface NavItem {
  label: string;
  icon: string;
  link: string;
  exact?: boolean;
}

/** תפריט לכל תפקיד: מעט פריטים, אייקון ושם לכל אחד */
const NAV: Record<string, NavItem[]> = {
  INVESTOR: [
    { label: 'היעדים שלי', icon: 'flag', link: '/investor', exact: true },
    { label: 'הצעות שקיבלתי', icon: 'mail', link: '/investor/offers' },
    { label: 'השוואת מוצרים', icon: 'compare_arrows', link: '/products' },
    { label: 'פרופיל סיכון', icon: 'speed', link: '/investor/risk' },
    { label: 'עזרה ומדריך', icon: 'menu_book', link: '/help' },
  ],
  AGENT: [
    { label: 'לידים ודשבורד', icon: 'dashboard', link: '/agent', exact: true },
    { label: 'המוצרים שלי', icon: 'inventory_2', link: '/agent/products' },
    { label: 'קטלוג מוצרים', icon: 'compare_arrows', link: '/products' },
    { label: 'עזרה ומדריך', icon: 'menu_book', link: '/help' },
  ],
};

/** הפעולה החשובה ביותר לכל תפקיד – כפתור בולט בראש התפריט */
const PRIMARY: Record<string, { label: string; link: string }> = {
  INVESTOR: { label: 'יעד חדש', link: '/investor/goals/new' },
  AGENT: { label: 'מוצר חדש', link: '/agent/products/new' },
};

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatButtonModule, NotificationBell],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly auth = inject(AuthService);
  private readonly tour = inject(TourService);
  protected readonly user = this.auth.user;
  protected readonly menuOpen = signal(false);

  protected readonly navItems = computed(() => NAV[this.user()?.role ?? ''] ?? []);
  protected readonly primaryAction = computed(() => PRIMARY[this.user()?.role ?? ''] ?? null);
  protected readonly home = computed(() => {
    const role = this.user()?.role;
    return role ? homeRouteForRole(role) : '/auth/login';
  });

  constructor() {
    // אחרי רענון של דף בלי Guard (עזרה, מצב המערכת) משחזרים את ההתחברות מה-Refresh token
    this.auth.ensureAccess().subscribe();
    // סיור היכרות בכניסה הראשונה של כל תפקיד
    effect(() => this.tour.maybeShow(this.user()?.role));
  }

  protected roleLabel(role: string): string {
    return role === 'AGENT' ? 'סוכן' : role === 'INVESTOR' ? 'משקיע' : role;
  }

  protected initials(name: string): string {
    const parts = (name ?? '').trim().split(/\s+/).filter(Boolean);
    return parts.slice(0, 2).map((part) => part[0]).join('') || '?';
  }

  protected closeMenu(): void {
    this.menuOpen.set(false);
  }

  protected logout(): void {
    this.closeMenu();
    this.auth.logout().subscribe();
  }
}
