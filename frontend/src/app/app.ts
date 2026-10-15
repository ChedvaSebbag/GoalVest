import { Component, effect, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';
import { AuthService } from './core/auth/auth.service';
import { TourService } from './core/help/tour.service';
import { NotificationBell } from './shell/notification-bell';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatToolbarModule, MatButtonModule, NotificationBell],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly auth = inject(AuthService);
  private readonly tour = inject(TourService);
  protected readonly user = this.auth.user;

  constructor() {
    // סיור היכרות בכניסה הראשונה של כל תפקיד
    effect(() => this.tour.maybeShow(this.user()?.role));
  }

  protected roleLabel(role: string): string {
    return role === 'AGENT' ? 'סוכן' : role === 'INVESTOR' ? 'משקיע' : role;
  }

  protected logout(): void {
    this.auth.logout().subscribe();
  }
}
