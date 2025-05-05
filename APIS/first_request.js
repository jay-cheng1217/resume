// const request=require('request');
const rp=require('request-promise');
// 另一種寫法
rp('http://www.omdbapi.com/?s=guardians+of+the+galaxy&apikey=thewdb')
    .then((body)=>{
        const parseAPI=JSON.parse(body);
        console.log(parseAPI);
    })
    .catch((err)=>{
        console.log('error',err);
    });

// request('https://jsonplaceholder.typicode.com/users/1',(Error,response,body)=>{
//     if(!Error && response.statusCode==200){
//         const parseAPI=JSON.parse(body);
//         console.log(`${parseAPI.name}`);
//     }
// });