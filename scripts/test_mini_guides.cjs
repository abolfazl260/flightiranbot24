const {chromium}=require('playwright');
const http=require('http'),fs=require('fs'),path=require('path'),assert=require('assert');
const repo=path.resolve(__dirname,'..');
(async()=>{
 const server=http.createServer((req,res)=>{let p=new URL(req.url,'http://localhost').pathname;
 p=p.startsWith('/assets/')?'src/flightiran/webapp/static/'+p.slice(8):'src/flightiran/webapp/static/index.html';
 try{res.setHeader('Content-Type',p.endsWith('.mjs')||p.endsWith('.js')?'text/javascript':p.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync(path.join(repo,p)));}catch{res.statusCode=404;res.end();}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:390,height:844}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.Telegram={WebApp:{initData:'test-only',ready(){},expand(){},BackButton:{show(){},hide(){},onClick(fn){window.guideBack=fn;}}}}});
 let unavailable=false,reads=0;
 await page.route('https://telegram.org/**',r=>r.fulfill({body:''}));
 await page.route('**/api/**',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(r.request().url().includes('bootstrap')?{user:{first_name:'مسافر'},countries:[],passport:'IR',links:{}}:{routes:[],rules:[]})}));
 await page.route('https://raw.githubusercontent.com/**',r=>{reads++;assert(!r.request().headers()['x-telegram-init-data']);if(unavailable)return r.abort();
 const p=r.request().url().split('/main/')[1];return r.fulfill({contentType:'application/json',body:fs.readFileSync(path.join(repo,p),'utf8')});});
 await page.goto('http://127.0.0.1:'+server.address().port);await page.locator('[data-go=airlines]').click();
 await page.getByRole('button',{name:/ایران‌ایر/}).waitFor();await page.getByLabel('جست‌وجوی نام یا کد').fill('uae');
 await page.getByRole('button',{name:/امارات/}).click();await page.getByRole('button',{name:/ناوگان هواپیما/}).click();
 await page.getByRole('heading',{name:'Airbus A350'}).waitFor();assert.equal(await page.locator('#airlines-guide').evaluate(e=>e.scrollWidth<=e.clientWidth+1),true);
 await page.getByRole('button',{name:'بازگشت',exact:true}).click();await page.getByRole('button',{name:/بار مجاز و اقلام خاص/}).waitFor();
 const n=reads;await page.getByRole('button',{name:'بازگشت',exact:true}).click();assert.equal(reads,n);
 unavailable=true;await page.getByRole('button',{name:'بررسی دوباره اطلاعات',exact:true}).click();await page.getByText(/نسخهٔ همین نشست/).waitFor();unavailable=false;
 await page.evaluate(()=>window.guideBack());await page.locator('[data-go=airports]').click();await page.getByRole('button',{name:/امام خمینی تهران/}).click();
 await page.getByRole('button',{name:/بار مجاز و قوانین حمل بار/}).click();await page.getByRole('heading',{name:'بار مجاز و قوانین حمل بار'}).waitFor();
 assert.deepEqual(errors,[]);console.log('Browser smoke passed: airline search/fleet/back/offline + airport details, no credential leak or page errors.');
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exit(1)});
