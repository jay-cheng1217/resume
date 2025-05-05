const express=require('express');
const app=express();

// 抓取post後body值
const bodyParser=require('body-parser');
app.use(bodyParser.urlencoded({extended:true}));
let campgrounds=
    [
        {name:'Salmon Creek',img:'https://cdn.pixabay.com/photo/2017/09/26/13/50/rv-2788677__340.jpg'},
        {name:'Granite Hill',img:'https://cdn.pixabay.com/photo/2016/01/26/23/32/camp-1163419__340.jpg'},
        {name:'Mountain Goat\'s Rest',img:'https://cdn.pixabay.com/photo/2016/08/28/17/05/camping-1626412__340.jpg'}
    ]


app.set('view engine','ejs');

// 首頁
app.get('/',function(req,res){
    res.render('landing');
});

// 顯示結果
app.get('/campgrounds',function(req,res){
    res.render('campgrounds',{campgrounds:campgrounds});
});


// newpage新增後抓取body值
app.post('/campgrounds',function(req,res){
    let name=req.body.name;
    let img=req.body.img;
    let addCampgrounds={name:name,img:img}
    campgrounds.push(addCampgrounds);
    // post後回到campgrounds頁面
    res.redirect('/campgrounds');
});

app.get('/campgrounds/new',function(req,res){
    res.render('new.ejs');
});

app.listen(3002,function(){
    console.log('YelpCamp connect');
});