import { Component, OnInit } from '@angular/core';
import { ApiService } from './api.service';
import { HttpClientModule } from '@angular/common/http';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  title(title: any) {
    throw new Error('Method not implemented.');
  }
  statisticsData: any;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.fetchStatistics();
    setInterval(() => {
      this.fetchStatistics(); // Aktualisiere die Daten alle 60 Sekunden
    }, 6000);
  }

  fetchStatistics() {
    //alert("ghjk");
    this.apiService.getStatistics().subscribe(data => {
      this.statisticsData = data;
      console.log(this.statisticsData.bpi.EUR.rate);
      console.log(this.statisticsData.bpi.GBP.rate);
      console.log(this.statisticsData.bpi.USD.rate);
    });
  }
}
