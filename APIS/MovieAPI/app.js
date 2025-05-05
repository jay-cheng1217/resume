const express = require('express');
const axios = require('axios');
const app = express();

app.set("view engine", 'ejs');

// 顯示搜尋畫面
app.get('/', (req, res) => {
    res.render('search'); // views/search.ejs
});

// 顯示搜尋結果
app.get('/results', async (req, res) => {
    const search = req.query.search;

    if (!search) {
        return res.send('請輸入搜尋關鍵字');
    }

    const url = `http://www.omdbapi.com/?s=${encodeURIComponent(search)}&apikey=thewdb`;

    try {
        const response = await axios.get(url);
        const data = response.data;

        if (data.Response === 'False') {
            return res.send(`找不到資料：${data.Error}`);
        }

        res.render('results', { data });
    } catch (error) {
        console.error('API 呼叫失敗:', error.message);
        res.status(500).send('伺服器發生錯誤，請稍後再試');
    }
});

// 啟動伺服器
app.listen(3002, () => {
    console.log('movieAPI server running at http://localhost:3002');
});
