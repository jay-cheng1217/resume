var average=function(num){
    return (Math.round(num.reduce((i,j)=>i+j)/num.length));
    var i=0;
    num.forEach(element => {
        i+=element;
    });
    console.log(Math.round(i/num.length));
}

var scores=[90,98,89,100,100,86,94];
var scores2=[40,65,77,82,80,54,73,63,95,49];
console.log(average(scores));console.log(average(scores2));