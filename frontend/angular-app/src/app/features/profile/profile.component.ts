import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthApiService } from '../auth/auth-api.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css'],
})
export class ProfileComponent {
  private readonly router = inject(Router);
  private readonly authApi = inject(AuthApiService);

  readonly state = (this.router.getCurrentNavigation()?.extras.state ?? window.history.state) as {
    userDetails?: {
      name?: string;
      email?: string;
      mode?: string;
      rememberMe?: boolean;
      agreeToTerms?: boolean;
    };
  };

  get userDetails() {
    return this.authApi.getUserDetails() ?? this.state.userDetails ?? {
      name: 'Shizen Bank customer',
      email: 'customer@example.com',
      mode: 'login',
      rememberMe: true,
      agreeToTerms: true,
    };
  }
}
