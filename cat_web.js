$(window).scroll(function(e){
    if($(window).scrollTop()!=0){
        $('.explore').addClass('at_top');
        $('.navbar').addClass('navbar_top');
    }else{
        $('.explore').removeClass('at_top');
        $('.navbar').removeClass('navbar_top');
    }
});

$(document).on('click','.nav-link,.navbar-brand',function(e){
    e.preventDefault();
    var target=$(this).attr('href');
    console.log(target);
    $("html,body").animate({
        scrollTop: $(target).offset().top
      },500)
      
});
function detect_cat(cat_id,x){
  var catplace=$(cat_id).offset().left+$(cat_id).width()/2;
  if(Math.abs(x-catplace)<80){
    $(cat_id).css("bottom","0px") 
  }else{
    $(cat_id).css("bottom","-50px") 
  }
}

$(window).mousemove(function(e){
  var pagex=e.pageX;
  var pagey=e.pageY;
  var x=pagex-$('#section_about').offset().left;
  var y=pagey-$('#section_about').offset().top;
  
  detect_cat("#cat_yellow",pagex);
  detect_cat("#cat_blue",pagex);
  detect_cat("#cat_grey",pagex);

  if(y<0 || y>$("#section_about").outerHeight()){
    $("#cross").css("opacity",0);
  }else{
    $("#cross").css("opacity",1);
  }
  
  $("#cross").css("left",x+"px");
  $("#cross").css("top",y+"px");
  
  var catplace=$("#cat").offset().left+$("#cat").width()/2;
  var catplacetop=$("#cat").offset().top;
  var cat_url="http://awiclass.monoame.com/catpic/";
  if(pagex<catplace-50){
    $("#cat").attr("src",cat_url+"cat_left.png");
  }else if(pagex>catplace+50){
    $("#cat").attr("src",cat_url+"cat_right.png");
  }else{
    $("#cat").attr("src",cat_url+"cat_top.png");
  }

  if(pagex<catplace-50 && pagey<catplacetop){
    $("#cat").attr("src",cat_url+"cat_lefttop.png");
  }else if(pagex>catplace+50 && pagey<catplacetop){
    $("#cat").attr("src",cat_url+"cat_righttop.png");
  }
  

  $('.mountain,.mountain_ice').css('transform','translateX('+(pagex/20+50)+'px)');
  $('.r1text').css('transform','translateX('+(y/-5)+'px)');
  $('.r2text').css('transform','translateX('+(y/-10)+'px)');
  $('.r3text').css('transform','translateX('+(y/-15)+'px)');
  $('.tri1').css('transform','translateX('+(x/-5)+'px)');
  $('.tri2').css('transform','translateX('+(x/-10)+'px)');
  $('.tri3').css('transform','translateX('+(x/-15)+'px)');
  $('.tri4').css('transform','translateX('+(x/-20)+'px)');
  $('.tri5').css('transform','translateX('+(x/-25)+'px)');


});



  

var vm = new Vue({
    el:"#app",
    data:{
      works: []
    },  
    mounted: function(){
      var vobj=this;
      $.ajax({
        url:"https://awiclass.monoame.com/api/command.php?type=get&name=projects",
        success: function(res){
          vobj.works=JSON.parse(res);
        }
        
      });
    }
  });