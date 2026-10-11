import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { HealthResponse, SystemQueriesService } from '../../core/system/system-queries.service';

interface Row { key: 'database' | 'ollama' | 'chroma'; label: string; hint: string; }

@Component({
  selector: 'gv-system-status',
  imports: [MatCardModule, MatButtonModule, MatProgressBarModule],
  templateUrl: './system-status.html',
  styleUrl: './system-status.scss',
})
export class SystemStatus {
  private readonly queries = inject(SystemQueriesService);

  protected readonly rows: Row[] = [
    { key: 'database', label: 'מסד נתונים (Somee)', hint: 'Event Store וטבלאות קריאה' },
    { key: 'ollama', label: 'מודל שפה (Ollama)', hint: 'LLM והטמעות לסוכן ה-AI' },
    { key: 'chroma', label: 'מסד וקטורי (ChromaDB)', hint: 'חיפוש סמנטי ו-RAG' },
  ];

  protected readonly loading = signal(true);
  protected readonly health = signal<HealthResponse | null>(null);
  protected readonly apiError = signal(false);

  constructor() { this.refresh(); }

  refresh(): void {
    this.loading.set(true);
    this.apiError.set(false);
    this.queries.getHealth().subscribe({
      next: (h) => { this.health.set(h); this.loading.set(false); },
      // השרת מחזיר 503 עם גוף JSON כשחלק מהרכיבים לא תקינים
      error: (e) => {
        if (e?.error?.checks) { this.health.set(e.error as HealthResponse); }
        else { this.health.set(null); this.apiError.set(true); }
        this.loading.set(false);
      },
    });
  }
}
