var express=require('Express');
var app=express();
app.get('/',function(req,res){
    res.send('Hi there, welcome to my assignment!');
});
app.get('/speak/:animal',function(req,res){
    var animal= req.params.animal;
    var sound={
        pig:'Oink',
        cow:'Moo',
        dog:'woof woof',
        cat:'I hate you humen'
    }
    res.send('The '+animal+' says '+sound[animal]);
    
});

app.get('/repeat/:say/:num',function(req,res){
    var say=req.params.say;
    var num=Number(req.params.num);
    var result="";
    
    for(var i=0;i<num;i++){
        result+=say+' ';
    }
    res.send(result);
});

app.get('*',function(req,res){
    res.send('sorry,page not found...What are you doing with your life');
});
app.listen(3001,function(){
    console.log('connect');
});
// console.log(express);