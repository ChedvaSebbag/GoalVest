import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { Institution, UserProfile } from './auth.models';

/** קריאה: המשתמש המחובר ורשימת הגופים להרשמה. */
@Injectable({ providedIn: 'root' })
export class AuthQueriesService {
  private readonly http = inject(HttpClient);

  me(): Observable<UserProfile> {
    return this.http.get<UserProfile>('/api/auth/me');
  }

  institutions(): Observable<Institution[]> {
    return this.http.get<{ items: Institution[] }>('/api/institutions').pipe(map((body) => body.items));
  }
}
