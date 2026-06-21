import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface AuthEventRequest {
  mode: 'login' | 'register';
  email: string;
  firstName?: string;
  lastName?: string;
  rememberMe?: boolean;
  agreeToTerms?: boolean;
  source: string;
}

export interface AuthEventResponse {
  insertedId: string;
  createdAt: string;
  message: string;
}

@Injectable({
  providedIn: 'root',
})
export class AuthApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000';

  recordAuthEvent(payload: AuthEventRequest): Observable<AuthEventResponse> {
    return this.http.post<AuthEventResponse>(`${this.baseUrl}/api/auth/records`, payload);
  }
}