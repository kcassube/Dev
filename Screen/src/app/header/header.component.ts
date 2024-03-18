import { Component } from '@angular/core';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent {
  imageLeftPosition: number = 800;
  moveRight: boolean = true;
  colors: string[] = ['#0022ff', '#0031ff', '#0400ff'];
  
    
  
  ngOnInit() {

  
    setInterval(() => {
      if (this.moveRight) {
        //this.imageLeftPosition++;
        this.imageLeftPosition += 1;
      } else {
        //this.imageLeftPosition--;
        this.imageLeftPosition-=1;
      }
      if (this.imageLeftPosition >= 800) { 
        this.moveRight = false;
      } else if (this.imageLeftPosition <= 780) {
        this.moveRight = true;
      }
      console.log(this.moveRight);
      console.log(this.imageLeftPosition);
      
    }, 500); 
  }
}


