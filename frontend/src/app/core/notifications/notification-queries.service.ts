import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AppNotification } from './notification.models';

@Injectable({ providedIn: 'root' })
export class NotificationQueriesService {
  private readonly http = inject(HttpClient);

  list(): Observable<{ items: AppNotification[] }> {
    return this.http.get<{ items: AppNotification[] }>('/api/notifications', {
      params: new HttpParams(),
    });
  }

  unreadCount(): Observable<{ count: number }> {
    return this.http.get<{ count: number }>('/api/notifications/unread-count');
  }
}
