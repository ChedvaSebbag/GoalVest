import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CommandResult } from '../investor/investor.models';

@Injectable({ providedIn: 'root' })
export class NotificationCommandsService {
  private readonly http = inject(HttpClient);

  markRead(id: string): Observable<CommandResult> {
    return this.http.post<CommandResult>(`/api/notifications/${id}/read`, {}, {
      headers: { 'Idempotency-Key': crypto.randomUUID() },
    });
  }
}
