var express=require('express');
var app=express();
var bodyParser=require('body-parser');
// 讀取post抓取值
app.use(bodyParser.urlencoded({extended:true}));

app.set('view engine','ejs');
var friends=['Tony','Miranda','Justin','Pierre','Lily'];
var delfriend;var addfriend;
app.get('/',function(req,res){
    res.render('home');
});
// 新增元素
app.post('/getfriend',function(req,res){
    addfriend=req.body.newfriend;
    if(addfriend!=""){
        friends.push(addfriend);
    }
    res.redirect('/friend');
});
// 刪除元素

app.post('/delfriend',function(req,res){
    delfriend=req.body.delfriend;
    delfriend=friends.findIndex((element) => element == delfriend);
    if(delfriend!=-1){
        console.log(delfriend);
        friends.splice(delfriend,1);
    }
    res.redirect('/friend');
});
app.get('/friend',function(req,res){
    res.render('friend',{friends:friends});
});

app.listen(3002,function(){
    console.log('connect');
});