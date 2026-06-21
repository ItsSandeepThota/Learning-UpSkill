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

  constructor() {
    this.authApi.clearUserDetails();
  }

  mode: AuthMode = 'login';
  loading = false;
  statusMessage = '';
  statusTone: StatusTone = 'info';
  showVerificationForm = false;
  verificationEmail = '';

  readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    rememberMe: [true],
  });

  readonly registerForm = this.formBuilder.nonNullable.group({
    firstName: ['', [Validators.required, Validators.minLength(2), Validators.pattern('^[a-zA-Z\\s\\-]+$')]],
    lastName: ['', [Validators.required, Validators.minLength(2), Validators.pattern('^[a-zA-Z\\s\\-]+$')]],
    email: ['', [Validators.required, Validators.email]],
    password: [
      '',
      [
        Validators.required,
        Validators.minLength(10),
        Validators.pattern('^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{10,}$'),
      ],
    ],
    confirmPassword: ['', [Validators.required]],
    agreeToTerms: [false, [Validators.requiredTrue]],
  });

  readonly verificationForm = this.formBuilder.nonNullable.group({
    code: ['', [Validators.required, Validators.minLength(6), Validators.maxLength(6), Validators.pattern('^[0-9]{6}$')]],
  });

  setMode(mode: AuthMode): void {
    this.mode = mode;
    this.statusMessage = '';
    this.statusTone = 'info';
    this.showVerificationForm = false;
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
        password: this.mode === 'login' ? this.loginForm.controls.password.value : this.registerForm.controls.password.value,
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

      console.log('Auth response payload:', response);
      if (this.mode === 'register' && (response.insertedId === 'pending' || (response as any)['inserted_id'] === 'pending')) {
        this.showVerificationForm = true;
        this.verificationEmail = payload.email;
        this.loading = false;
        return;
      }

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

      const userDetails = this.buildUserDetails(payload);
      this.authApi.setUserDetails(userDetails);

      await this.router.navigate(['/dashboard'], {
        state: {
          userDetails,
          mode: this.mode,
          record: response,
          message: successMessage,
        },
      });
    } catch (error: any) {
      this.statusTone = 'error';
      this.statusMessage = error?.error?.detail || 'We could not save your request. Please try again.';
    } finally {
      this.loading = false;
    }
  }

  async submitVerification(): Promise<void> {
    if (this.verificationForm.invalid) {
      this.verificationForm.markAllAsTouched();
      this.statusTone = 'error';
      this.statusMessage = 'Please enter a valid 6-digit verification code.';
      return;
    }

    this.loading = true;
    this.statusMessage = '';

    try {
      const code = this.verificationForm.controls.code.value;
      const response = await firstValueFrom(this.authApi.verifyRegistration(this.verificationEmail, code));

      this.statusTone = 'success';
      this.statusMessage = response.message || 'Verification successful!';

      const userDetails = {
        name: `${this.registerForm.controls.firstName.value} ${this.registerForm.controls.lastName.value}`.trim() || this.verificationEmail.split('@')[0],
        email: this.verificationEmail,
        mode: 'register' as AuthMode,
        rememberMe: false,
        agreeToTerms: this.registerForm.controls.agreeToTerms.value,
      };

      this.authApi.setUserDetails(userDetails);

      this.registerForm.reset();
      this.verificationForm.reset();
      this.showVerificationForm = false;

      await this.router.navigate(['/dashboard'], {
        state: {
          userDetails,
          mode: 'register',
          record: response,
          message: response.message,
        },
      });
    } catch (error: any) {
      this.statusTone = 'error';
      this.statusMessage = error?.error?.detail || 'Verification failed. Please check your code and try again.';
    } finally {
      this.loading = false;
    }
  }

  cancelVerification(): void {
    this.showVerificationForm = false;
    this.verificationEmail = '';
    this.verificationForm.reset();
    this.statusMessage = '';
    this.statusTone = 'info';
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

    if (control.hasError('maxlength')) {
      const requiredLength = control.errors['maxlength'].requiredLength;
      return `Please use at most ${requiredLength} characters.`;
    }

    if (control.hasError('requiredTrue')) {
      return 'Please accept the terms to continue.';
    }

    if (control.hasError('pattern')) {
      if (control === this.registerForm.get('password')) {
        return 'Password must contain uppercase, lowercase, numbers, and special characters.';
      }
      if (control === this.registerForm.get('firstName') || control === this.registerForm.get('lastName')) {
        return 'Name can only contain letters, spaces, and hyphens.';
      }
      if (control === this.verificationForm.get('code')) {
        return 'Code must be exactly 6 digits.';
      }
      return 'Please format this input correctly.';
    }

    return 'Please enter a valid value.';
  }

  get activeForm() {
    return this.mode === 'login' ? this.loginForm : this.registerForm;
  }

  get pageTitle(): string {
    if (this.showVerificationForm) {
      return 'Verify your Gmail';
    }
    return this.mode === 'login' ? 'Welcome to Shizen Bank' : 'Open your Shizen Bank profile';
  }

  get pageCopy(): string {
    if (this.showVerificationForm) {
      return 'Complete registration by verifying your email address.';
    }
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
