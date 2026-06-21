import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface AuthEventRequest {
  mode: 'login' | 'register';
  email: string;
  password: string;
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

export interface UserDetails {
  name: string;
  email: string;
  mode: 'login' | 'register';
  rememberMe?: boolean;
  agreeToTerms?: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class AuthApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000';

  private userDetails: UserDetails | null = null;

  recordAuthEvent(payload: AuthEventRequest): Observable<AuthEventResponse> {
    return this.http.post<AuthEventResponse>(`${this.baseUrl}/api/auth/records`, payload);
  }

  verifyRegistration(email: string, code: string): Observable<AuthEventResponse> {
    return this.http.post<AuthEventResponse>(`${this.baseUrl}/api/auth/verify`, { email, code });
  }

  setUserDetails(details: UserDetails): void {
    this.userDetails = details;
    try {
      localStorage.setItem('user_details', JSON.stringify(details));
    } catch {
      // ignore if localStorage is unavailable
    }
  }

  getUserDetails(): UserDetails | null {
    if (!this.userDetails) {
      try {
        const stored = localStorage.getItem('user_details');
        if (stored) {
          this.userDetails = JSON.parse(stored) as UserDetails;
        }
      } catch {
        // ignore
      }
    }
    return this.userDetails;
  }

  clearUserDetails(): void {
    this.userDetails = null;
    try {
      localStorage.removeItem('user_details');
    } catch {
      // ignore
    }
  }

  getProfile(email: string): Observable<ProfileDetails> {
    return this.http.get<ProfileDetails>(`${this.baseUrl}/api/profile/${email}`);
  }

  updateBalance(email: string, payload: { amount: number; currency: string; action: 'add' | 'deduct'; tx_title: string; tx_subtitle: string; tx_flag: string }): Observable<ProfileDetails> {
    return this.http.post<ProfileDetails>(`${this.baseUrl}/api/profile/${email}/update-balance`, payload);
  }

  addCard(email: string, payload: { type: 'debit' | 'credit'; color: string }): Observable<ProfileDetails> {
    return this.http.post<ProfileDetails>(`${this.baseUrl}/api/profile/${email}/add-card`, payload);
  }

  toggleCardFreeze(email: string, payload: { card_id: number }): Observable<ProfileDetails> {
    return this.http.post<ProfileDetails>(`${this.baseUrl}/api/profile/${email}/toggle-card-freeze`, payload);
  }

  updateCardLimit(email: string, payload: { card_id: number; limit: number }): Observable<ProfileDetails> {
    return this.http.post<ProfileDetails>(`${this.baseUrl}/api/profile/${email}/update-card-limit`, payload);
  }

  updateCardColor(email: string, payload: { card_id: number; color: string }): Observable<ProfileDetails> {
    return this.http.post<ProfileDetails>(`${this.baseUrl}/api/profile/${email}/update-card-color`, payload);
  }

  addContact(email: string, payload: { name: string; flag: string }): Observable<ProfileDetails> {
    return this.http.post<ProfileDetails>(`${this.baseUrl}/api/profile/${email}/add-contact`, payload);
  }
}

export interface CardDetails {
  id: number;
  number: string;
  holder: string;
  expiry: string;
  cvv: string;
  color: string;
  frozen: boolean;
  limit: number;
  type: 'debit' | 'credit';
}

export interface ContactDetails {
  name: string;
  initials: string;
  avatarUrl?: string;
  currency: string;
  flag: string;
}

export interface TransactionDetails {
  id: number;
  title: string;
  subtitle: string;
  amount: number;
  currency: string;
  flag: string;
  time: string;
  status: 'success' | 'pending' | 'failed';
}

export interface ProfileDetails {
  email: string;
  name: string;
  balance: number;
  currency: string;
  cards: CardDetails[];
  contacts: ContactDetails[];
  transactions: TransactionDetails[];
  first_name?: string;
  last_name?: string;
  phone_no?: string;
  location?: string;
  account_no?: string;
}