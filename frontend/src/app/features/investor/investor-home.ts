import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'gv-investor-home',
  imports: [RouterOutlet],
  template: `<router-outlet />`,
})
export class InvestorHome {}
