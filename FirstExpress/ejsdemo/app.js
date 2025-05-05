var express=require('express');
var app=express();

app.get('/',function(req,res){
    res.render('home.ejs');
    // res.send('welcome to my home page');
});
app.get('/fellinlovewith/:thing',function(req,res){
    var thing=req.params.thing;
    res.render("love.ejs",{thingVal:thing})
    // res.send('welcome to my home page');
});
app.get('/post',function(req,res){
    var posts=[
        {title:'Post1',author:'Susy'},
        {title:'My adorable pet bunny',author:'Charlie'},
        {title:'Can you believe this pomsky?',author:'Colt'}
    ];
    res.render("posts.ejs",{posts:posts});

});
app.listen(3002,function(){
    console.log('connect');
});