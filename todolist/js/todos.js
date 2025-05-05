$("ul").on("click","li",function(){
	$(this).toggleClass("clickFinalize");
});

$("#addItem").on("keypress",function(e){
	if(e.which===13){
		if($(this).val()!=""){
			var todoitem=$(this).val();
			$("ul").append("<li><span class=\"dele\"><i class='fas fa-trash-alt'></i></span> "+todoitem+"</li>");
			$(this).val("");
		}
		
	}
});

$("ul").on("click",".dele",function(e){
	// parent讓整個父元素一併淡出刪除
	$(this).parent().fadeOut(500,function(){
		$(this).remove();
	});
	// 讓此event不會影響父元素事件 li的Class
	e.stopPropagation();
});

var minus=true;
$("h1").on("click",".minus",function(){
	$("#addItem").slideToggle();
	if(minus===true){
		$("h1").html("TO-DO LIST<i class=\"fas fa-plus minus\"></i>");
		
	}else{
		$("h1").html("TO-DO LIST<i class=\"fas fa-minus minus\"></i>");
	}
	minus=!minus;

	
});
