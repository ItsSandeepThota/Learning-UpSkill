import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthApiService } from './auth-api.service';

type AuthMode = 'login' | 'register';

type StatusTone = 'success' | 'error' | 'info';

@Component({
  selector: 'app-auth-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './auth.component.html',
  styleUrls: ['./auth.component.css'],
})
export class AuthComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authApi = inject(AuthApiService);
  private readonly router = inject(Router);

  mode: AuthMode = 'login';
  loading = false;
  statusMessage = '';
  statusTone: StatusTone = 'info';

  readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    rememberMe: [true],
  });

  readonly registerForm = this.formBuilder.nonNullable.group({
    firstName: ['', [Validators.required, Validators.minLength(2)]],
    lastName: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', [Validators.required]],
    agreeToTerms: [false, [Validators.requiredTrue]],
  });

  setMode(mode: AuthMode): void {
    this.mode = mode;
    this.statusMessage = '';
    this.statusTone = 'info';
  }

  async submit(): Promise<void> {
    const form = this.mode === 'login' ? this.loginForm : this.registerForm;

    if (form.invalid) {
      form.markAllAsTouched();
      this.statusTone = 'error';
      this.statusMessage = 'Please complete the form to continue.';
      return;
    }

    if (this.mode === 'register') {
      const password = this.registerForm.controls.password.value;
      const confirmPassword = this.registerForm.controls.confirmPassword.value;

      if (password !== confirmPassword) {
        this.statusTone = 'error';
        this.statusMessage = 'Passwords do not match.';
        return;
      }
    }

    this.loading = true;

    try {
      const payload = {
        mode: this.mode,
        email: this.mode === 'login' ? this.loginForm.controls.email.value : this.registerForm.controls.email.value,
        firstName: this.mode === 'register' ? this.registerForm.controls.firstName.value : undefined,
        lastName: this.mode === 'register' ? this.registerForm.controls.lastName.value : undefined,
        rememberMe: this.mode === 'login' ? this.loginForm.controls.rememberMe.value : undefined,
        agreeToTerms: this.mode === 'register' ? this.registerForm.controls.agreeToTerms.value : undefined,
        source: 'web-auth-page',
      };

      const response = await firstValueFrom(this.authApi.recordAuthEvent(payload));
      const successMessage =
        response.message || (this.mode === 'login' ? 'Sign in recorded successfully.' : 'Account request recorded successfully.');

      this.statusTone = 'success';
      this.statusMessage = successMessage;

      form.reset(
        this.mode === 'login'
          ? { email: '', password: '', rememberMe: true }
          : {
              firstName: '',
              lastName: '',
              email: '',
              password: '',
              confirmPassword: '',
              agreeToTerms: false,
            },
      );

      await this.router.navigate(['/dashboard'], {
        state: {
          userDetails: this.buildUserDetails(payload),
          mode: this.mode,
          record: response,
          message: successMessage,
        },
      });
    } catch {
      this.statusTone = 'error';
      this.statusMessage = 'We could not save your request. Please try again.';
    } finally {
      this.loading = false;
    }
  }

  getControlError(control: AbstractControl | null): string | null {
    if (!control || !control.touched || !control.errors) {
      return null;
    }

    if (control.hasError('required')) {
      return 'This field is required.';
    }

    if (control.hasError('email')) {
      return 'Please enter a valid email address.';
    }

    if (control.hasError('minlength')) {
      const requiredLength = control.errors['minlength'].requiredLength;
      return `Please use at least ${requiredLength} characters.`;
    }

    if (control.hasError('requiredTrue')) {
      return 'Please accept the terms to continue.';
    }

    return 'Please enter a valid value.';
  }

  get activeForm() {
    return this.mode === 'login' ? this.loginForm : this.registerForm;
  }

  get pageTitle(): string {
    return this.mode === 'login' ? 'Welcome to Shizen Bank' : 'Open your Shizen Bank profile';
  }

  get pageCopy(): string {
    return this.mode === 'login'
      ? 'Access your accounts, cards, and transfers from one secure dashboard.'
      : 'Create a profile for a seamless banking experience on web and mobile.';
  }

  private buildUserDetails(payload: Record<string, unknown>) {
    return {
      name:
        this.mode === 'register'
          ? `${(payload['firstName'] as string | undefined) ?? ''} ${(payload['lastName'] as string | undefined) ?? ''}`.trim()
          : (payload['email'] as string).split('@')[0],
      email: payload['email'] as string,
      mode: this.mode,
      rememberMe: payload['rememberMe'] as boolean | undefined,
      agreeToTerms: payload['agreeToTerms'] as boolean | undefined,
    };
  }
}
