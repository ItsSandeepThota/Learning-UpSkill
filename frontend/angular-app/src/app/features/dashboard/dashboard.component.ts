import { CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthApiService, UserDetails, ProfileDetails } from '../auth/auth-api.service';

interface DashboardState {
  userDetails?: UserDetails;
  record?: {
    insertedId?: string;
    createdAt?: string;
    message?: string;
  };
  message?: string;
}

interface CurrencyInfo {
  code: string;
  symbol: string;
  rate: number;
  flag: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly authApi = inject(AuthApiService);

  readonly state = (this.router.getCurrentNavigation()?.extras.state ?? window.history.state) as DashboardState;

  // Local properties mapped from backend ProfileDetails
  baseBalance = 0;
  cards: any[] = [];
  favorites: any[] = [];
  transactions: any[] = [];
  profileName = '';
  profileEmail = '';
  phoneNo = '';
  location = '';
  accountNo = '';

  readonly currencies: CurrencyInfo[] = [
    { code: 'GHS', symbol: 'GH₵', rate: 15.0, flag: '🇬🇭' },
    { code: 'USD', symbol: '$', rate: 1.0, flag: '🇺🇸' },
    { code: 'EUR', symbol: '€', rate: 0.92, flag: '🇪🇺' },
    { code: 'GBP', symbol: '£', rate: 0.79, flag: '🇬🇧' },
    { code: 'INR', symbol: '₹', rate: 83.5, flag: '🇮🇳' },
  ];

  selectedCurrency = 'GHS';
  showCurrencyDropdown = false;

  activeTab: 'home' | 'cards' | 'contacts' | 'more' = 'home';
  activeModal: 'pay' | 'request' | 'airtime' | 'bill' | 'addContact' | 'addCard' | null = null;
  showNotifications = false;

  selectedCardId = 1;
  isCardFlipped = false;

  // Mock notifications kept in session
  notifications: any[] = [
    { id: 1, text: 'Welcome to your Secure Dashboard.', time: '1 hour ago', unread: true }
  ];

  // Forms
  payRecipient = '';
  payAmount: number | null = null;
  payNote = '';

  requestFrom = '';
  requestAmount: number | null = null;
  requestNote = '';

  airtimePhone = '';
  airtimeAmount: number | null = null;
  airtimeCarrier = 'SecureNet';

  billType = 'Utilities';
  billAmount: number | null = null;
  billAccount = '';

  newContactName = '';
  newContactFlag = '🇬🇭';

  newCardType: 'debit' | 'credit' = 'debit';
  newCardColor = 'blue';

  ngOnInit(): void {
    const email = this.userDetails.email;
    this.authApi.getProfile(email).subscribe({
      next: (profile) => {
        this.updateLocalState(profile);
      },
      error: (err) => {
        console.error('Failed to load profile', err);
      }
    });
  }

  updateLocalState(profile: ProfileDetails): void {
    this.baseBalance = profile.balance;
    this.cards = profile.cards;
    this.favorites = profile.contacts;
    this.transactions = profile.transactions;
    this.profileName = profile.name || '';
    this.profileEmail = profile.email || '';
    this.phoneNo = profile.phone_no || '';
    this.location = profile.location || '';
    this.accountNo = profile.account_no || '';
  }

  get userDetails(): UserDetails {
    return this.authApi.getUserDetails() ?? this.state.userDetails ?? {
      name: 'Secure Customer',
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

  get currentCurrencyInfo(): CurrencyInfo {
    return this.currencies.find(c => c.code === this.selectedCurrency) || this.currencies[0];
  }

  get displayedBalance(): string {
    const info = this.currentCurrencyInfo;
    const balance = this.baseBalance * info.rate;
    return balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  selectCurrency(code: string): void {
    this.selectedCurrency = code;
    this.showCurrencyDropdown = false;
  }

  toggleCurrencyDropdown(): void {
    this.showCurrencyDropdown = !this.showCurrencyDropdown;
  }

  get unreadNotificationCount(): number {
    return this.notifications.filter(n => n.unread).length;
  }

  markAllNotificationsRead(): void {
    this.notifications.forEach(n => n.unread = false);
  }

  toggleNotifications(): void {
    this.showNotifications = !this.showNotifications;
    if (this.showNotifications) {
      this.markAllNotificationsRead();
    }
  }

  get selectedCard(): any {
    return this.cards.find(c => c.id === this.selectedCardId) || this.cards[0];
  }

  selectCard(id: number): void {
    this.selectedCardId = id;
    this.isCardFlipped = false;
  }

  toggleCardFreeze(): void {
    const card = this.selectedCard;
    if (card) {
      this.authApi.toggleCardFreeze(this.userDetails.email, { card_id: card.id }).subscribe({
        next: (profile) => {
          this.updateLocalState(profile);
          this.addNotification(`Card ending in ${card.number.slice(-4)} status updated.`);
        },
        error: (err) => {
          alert('Failed to update card lock state.');
        }
      });
    }
  }

  changeCardColor(color: string): void {
    const card = this.selectedCard;
    if (card) {
      this.authApi.updateCardColor(this.userDetails.email, { card_id: card.id, color }).subscribe({
        next: (profile) => {
          this.updateLocalState(profile);
        },
        error: (err) => {
          alert('Failed to customize card color.');
        }
      });
    }
  }

  saveCardLimit(card: any): void {
    this.authApi.updateCardLimit(this.userDetails.email, { card_id: card.id, limit: card.limit }).subscribe({
      next: (profile) => {
        this.updateLocalState(profile);
      },
      error: (err) => {
        alert('Failed to update spending limit.');
      }
    });
  }

  openModal(type: 'pay' | 'request' | 'airtime' | 'bill' | 'addContact' | 'addCard'): void {
    this.activeModal = type;
    this.showCurrencyDropdown = false;
    this.showNotifications = false;

    if (type !== 'pay') {
      this.payRecipient = '';
    }
  }

  closeModal(): void {
    this.activeModal = null;
    this.resetForms();
  }

  resetForms(): void {
    this.payRecipient = '';
    this.payAmount = null;
    this.payNote = '';

    this.requestFrom = '';
    this.requestAmount = null;
    this.requestNote = '';

    this.airtimePhone = '';
    this.airtimeAmount = null;
    this.airtimeCarrier = 'SecureNet';

    this.billAmount = null;
    this.billAccount = '';

    this.newContactName = '';
    this.newContactFlag = '🇬🇭';
  }

  submitPay(): void {
    if (!this.payRecipient || !this.payAmount || this.payAmount <= 0) return;

    if (this.selectedCard?.frozen) {
      alert('Active card is locked.');
      return;
    }

    this.authApi.updateBalance(this.userDetails.email, {
      amount: this.payAmount,
      currency: this.selectedCurrency,
      action: 'deduct',
      tx_title: 'Outbound Transfer',
      tx_subtitle: `To ${this.payRecipient}`,
      tx_flag: this.currentCurrencyInfo.flag
    }).subscribe({
      next: (profile) => {
        this.updateLocalState(profile);
        this.addNotification(`Successfully sent ${this.currentCurrencyInfo.symbol}${this.payAmount} to ${this.payRecipient}.`);
        this.closeModal();
      },
      error: (err) => {
        alert(err.error?.detail || 'Failed to complete transaction.');
      }
    });
  }

  submitRequest(): void {
    if (!this.requestFrom || !this.requestAmount || this.requestAmount <= 0) return;

    this.authApi.updateBalance(this.userDetails.email, {
      amount: this.requestAmount,
      currency: this.selectedCurrency,
      action: 'add',
      tx_title: 'Inbound Request',
      tx_subtitle: `From ${this.requestFrom}`,
      tx_flag: this.currentCurrencyInfo.flag
    }).subscribe({
      next: (profile) => {
        this.updateLocalState(profile);
        this.addNotification(`Requested ${this.currentCurrencyInfo.symbol}${this.requestAmount} from ${this.requestFrom}.`);
        this.closeModal();
      },
      error: (err) => {
        alert('Failed to submit payment request.');
      }
    });
  }

  submitAirtime(): void {
    if (!this.airtimePhone || !this.airtimeAmount || this.airtimeAmount <= 0) return;

    if (this.selectedCard?.frozen) {
      alert('Active card is locked.');
      return;
    }

    this.authApi.updateBalance(this.userDetails.email, {
      amount: this.airtimeAmount,
      currency: this.selectedCurrency,
      action: 'deduct',
      tx_title: `${this.airtimeCarrier} Airtime`,
      tx_subtitle: `Mobile ${this.airtimePhone}`,
      tx_flag: this.currentCurrencyInfo.flag
    }).subscribe({
      next: (profile) => {
        this.updateLocalState(profile);
        this.addNotification(`Successfully topped up ${this.airtimePhone} with ${this.currentCurrencyInfo.symbol}${this.airtimeAmount}.`);
        this.closeModal();
      },
      error: (err) => {
        alert(err.error?.detail || 'Failed to buy top-up.');
      }
    });
  }

  submitBill(): void {
    if (!this.billAccount || !this.billAmount || this.billAmount <= 0) return;

    if (this.selectedCard?.frozen) {
      alert('Active card is locked.');
      return;
    }

    this.authApi.updateBalance(this.userDetails.email, {
      amount: this.billAmount,
      currency: this.selectedCurrency,
      action: 'deduct',
      tx_title: `${this.billType} Bill`,
      tx_subtitle: `Ref: ${this.billAccount}`,
      tx_flag: this.currentCurrencyInfo.flag
    }).subscribe({
      next: (profile) => {
        this.updateLocalState(profile);
        this.addNotification(`Successfully paid ${this.billType}: ${this.currentCurrencyInfo.symbol}${this.billAmount}.`);
        this.closeModal();
      },
      error: (err) => {
        alert(err.error?.detail || 'Failed to settle bill.');
      }
    });
  }

  submitAddContact(): void {
    if (!this.newContactName) return;

    this.authApi.addContact(this.userDetails.email, {
      name: this.newContactName,
      flag: this.newContactFlag
    }).subscribe({
      next: (profile) => {
        this.updateLocalState(profile);
        this.addNotification(`${this.newContactName} registered to beneficiaries.`);
        this.closeModal();
      },
      error: (err) => {
        alert('Failed to register beneficiary.');
      }
    });
  }

  payFavoriteContact(contact: any): void {
    this.openModal('pay');
    this.payRecipient = contact.name;
    this.selectedCurrency = contact.currency;
  }

  submitAddCard(): void {
    this.authApi.addCard(this.userDetails.email, {
      type: this.newCardType,
      color: this.newCardColor
    }).subscribe({
      next: (profile) => {
        this.updateLocalState(profile);
        this.addNotification(`Successfully generated new virtual card.`);
        this.closeModal();
      },
      error: (err) => {
        alert('Failed to spawn new virtual card.');
      }
    });
  }

  private addNotification(text: string): void {
    this.notifications.unshift({
      id: Date.now(),
      text,
      time: 'Just now',
      unread: true
    });
  }

  logout(): void {
    this.authApi.clearUserDetails();
    this.router.navigate(['/']);
  }
}
