import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

interface DashboardState {
  userDetails?: {
    name?: string;
    email?: string;
    mode?: string;
    rememberMe?: boolean;
    agreeToTerms?: boolean;
  };
  record?: {
    insertedId?: string;
    createdAt?: string;
    message?: string;
  };
  message?: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent {
  private readonly router = inject(Router);

  readonly state = (this.router.getCurrentNavigation()?.extras.state ?? window.history.state) as DashboardState;

  get userDetails() {
    return this.state.userDetails ?? {
      name: 'Shizen Bank customer',
      email: 'customer@example.com',
      mode: 'login',
    };
  }

  get record() {
    return this.state.record;
  }

  get message() {
    return this.state.message ?? 'Your account activity is ready to review.';
  }
}
