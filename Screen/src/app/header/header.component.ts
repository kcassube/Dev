import { Component } from '@angular/core';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent {
  imageLeftPosition: number = 0;
  moveRight: boolean = true;
  colors: string[] = ['#0022ff', '#0031ff', '#0400ff'];
  
    
  
  ngOnInit() {

  
    setInterval(() => {
      if (this.moveRight) {
        this.imageLeftPosition++;
      } else {
        this.imageLeftPosition--;
      }
      if (this.imageLeftPosition >= 1) { 
        this.moveRight = false;
      } else if (this.imageLeftPosition <= 1) {
        this.moveRight = true;
      }
      
      
    }, 500); 
  }
}


