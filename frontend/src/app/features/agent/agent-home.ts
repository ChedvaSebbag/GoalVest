import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

/** מעטפת לאזור הסוכן. הניווט נמצא בסרגל העליון (app.html). */
@Component({
  selector: 'gv-agent-home',
  imports: [RouterOutlet],
  template: `<router-outlet />`,
})
export class AgentHome {}
