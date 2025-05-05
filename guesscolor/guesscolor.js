var colorNum=6;
var colors=colorList(colorNum);
var squares = document.querySelectorAll(".square");
var pickedColor=pickColor();
var colorDP=document.getElementById("colorDP");
var message=document.getElementById("message");
var h1 =document.querySelector("h1");
var resetButton=document.getElementById("resetButton");
var modeButton=document.querySelectorAll(".mode");

colorDP.textContent=pickedColor;


// 重新套入新的顏色
resetButton.addEventListener("click",function(){
	reset();

});


// for(var i=0;i<modeButton.length;i++){
modeButton.forEach(function(mode,i){
	mode.addEventListener("click",function(){
		modeButton[0].classList.remove("select");
		modeButton[1].classList.remove("select");
		this.classList.add("select");
		this.textContent==="Easy"?colorNum=3:colorNum=6;
		reset();
	});
});
	
// }

// 使顏色套入全部方格中
squares.forEach(function(color,i){
	color.style.backgroundColor=colors[i];
	// 判斷按下之顏色是否正確
	color.addEventListener("click",function(){
		var cilckColor=this.style.backgroundColor;
		if(cilckColor===pickedColor){
			message.textContent="Correct";
			changeColor(squares);
			h1.style.backgroundColor=pickedColor;
			reset.textContent="Try Again!";
		}else{
			this.style.backgroundColor="#232323";
			message.textContent="Try Again!";
		}
	});
});



function reset(){
	this.textContent="New Color";
	//generate all new colors
	colors = colorList(colorNum);
	//pick a new random color from array
	pickedColor = pickColor();
	//change colorDisplay to match picked Color
	squares.forEach(function(color,i){
		if (colors[i]) {
			color.style.display="block";
			color.style.backgroundColor=colors[i];
		}else{
			color.style.display="none";
		}
	});
	// colorDisplay.textContent = pickedColor;
	colorDP.textContent=pickedColor;
	h1.style.backgroundColor="steelblue";
	message.textContent="";
}





// 答對後全部顏色變為正確答案的顏色
function changeColor(squares){
	squares.forEach(function(color){
		color.style.backgroundColor=pickedColor;
	})
}

// 隨機選擇其中一格顏色為答案
function pickColor(){
	var random=Math.floor(Math.random()*colors.length);
	return colors[random];
	
}

// 隨機挑選RGB顏色
function colorList(num){
	var arr=[];

	for(var i=0;i<num;i++){
		var r = Math.floor(Math.random()*255);
		var g = Math.floor(Math.random()*255);
		var b = Math.floor(Math.random()*255);
		arr.push("rgb("+r+", "+g+", "+b+")");
		
	}
	return arr;
}




