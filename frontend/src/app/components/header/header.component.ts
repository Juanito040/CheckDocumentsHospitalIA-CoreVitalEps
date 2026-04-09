import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models/user.model';
import { ConfirmDialogComponent } from '../confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
    MatDialogModule
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.css'
})
export class HeaderComponent implements OnInit {
  @Input() title = 'CoreVital · Sistema IA';
  @Output() menuToggle = new EventEmitter<void>();

  currentUser: User | null = null;

  constructor(private authService: AuthService, private dialog: MatDialog) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => this.currentUser = user);
  }

  logout(): void {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      width: '360px',
      panelClass: 'confirm-dialog-panel',
      data: {
        title: 'Cerrar sesión',
        message: '¿Estás seguro de que deseas cerrar sesión?',
        confirmLabel: 'Cerrar sesión',
        cancelLabel: 'Cancelar',
        type: 'danger',
        icon: 'logout'
      }
    });

    ref.afterClosed().subscribe(confirmed => {
      if (confirmed) this.authService.logout();
    });
  }

  get isAdmin(): boolean {
    return this.authService.isAdmin();
  }
}
