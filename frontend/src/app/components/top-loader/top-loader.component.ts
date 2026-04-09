import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-top-loader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './top-loader.component.html',
  styleUrl: './top-loader.component.css'
})
export class TopLoaderComponent implements OnInit, OnDestroy {
  visible = false;
  completing = false;

  private sub!: Subscription;
  private completeTimer: any;

  constructor(private router: Router) {}

  ngOnInit(): void {
    this.sub = this.router.events.subscribe(event => {
      if (event instanceof NavigationStart) {
        clearTimeout(this.completeTimer);
        this.completing = false;
        this.visible = true;
      } else if (
        event instanceof NavigationEnd ||
        event instanceof NavigationCancel ||
        event instanceof NavigationError
      ) {
        this.completing = true;
        this.completeTimer = setTimeout(() => {
          this.visible = false;
          this.completing = false;
        }, 400);
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    clearTimeout(this.completeTimer);
  }
}
