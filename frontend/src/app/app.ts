import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToastContainerComponent } from './components/toast-container/toast-container.component';
import { TopLoaderComponent } from './components/top-loader/top-loader.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, ToastContainerComponent, TopLoaderComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected title = 'frontend';
}
