import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = 'https://api.coindesk.com/v1/bpi/currentprice.json'; 
  statisticsData: any;

  constructor(private http: HttpClient) {}

  getStatistics(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}`);
    
  }
}