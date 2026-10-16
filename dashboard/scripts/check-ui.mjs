// Kiểm tra giao diện bằng Edge có sẵn và CDP, không cần thư viện trình duyệt.
import { spawn } from 'node:child_process';
import { createServer as createNetServer } from 'node:net';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import assert from 'node:assert/strict';
import { number, percent } from '../src/services/formatNumbers.js';
import { buildCsv, overviewTables } from '../src/services/overviewExport.js';
import { calculateOverview } from '../src/services/overviewMetrics.js';
import { durationFields } from '../src/services/watchDuration.js';
import { actionLabels as overviewActionLabels, hourRange } from '../src/content/overviewContent.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const selectedSource = JSON.parse(await readFile(new URL('../public/data/source.json',import.meta.url),'utf8'));
const sourceData = async name => JSON.parse(await readFile(new URL(`../public/data/${selectedSource.runId}/${name}`, import.meta.url), 'utf8'));
const dailyRows = await sourceData('stats_daily_active_users.json');
const actionRows = (await sourceData('stats_action_distribution.json')).sort((a,b) => b.count-a.count);
const hourlyRows = await sourceData('stats_hourly_activity.json');
const movieRows = await sourceData('stats_top_movies_by_play.json');
const genreRows = await sourceData('stats_top_genres.json');
const durationRows = (await sourceData('stats_watch_duration_summary.json'));
const combinedRows = (await sourceData('stats_user_movie_time.json'));
const clusteringMetadata = (await sourceData('kmeans_model_metadata.json'))[0];
const clusterProfiles = (await sourceData('kmeans_cluster_profiles.json'));
const clusterUsers = (await sourceData('kmeans_assignments.json')).sort((a,b) => a.userId.localeCompare(b.userId));
const overview = calculateOverview(actionRows,clusterUsers);
const expectedKpis = [overview.totalEvents,overview.distinctUsers,actionRows.find(row=>row.action==='play').count].map(number);
const artifacts = new URL(`../.browser-check/${Date.now()}/`, import.meta.url);
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const reserve = createNetServer();
await new Promise((resolve) => reserve.listen(0, '127.0.0.1', resolve));
const debugPort = reserve.address().port;
await new Promise((resolve) => reserve.close(resolve));
await mkdir(artifacts, { recursive: true });
const vite = await createServer({ root, server: { host: '127.0.0.1', port: 0, watch: { ignored: ['**/.browser-check/**'] } } });
await vite.listen();
const origin = `http://127.0.0.1:${vite.httpServer.address().port}`;
const browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', [
  '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=${debugPort}`,
  `--user-data-dir=${fileURLToPath(new URL('profile/', artifacts))}`, 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
let socket;
try {
  let target;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json/new?${origin}`, { method: 'PUT' });
      target = await response.json();
      break;
    } catch { await pause(100); }
  }
  assert.ok(target, 'Edge không mở cổng kiểm tra.');
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let id = 0;
  const pending = new Map();
  const errors = [];
  const downloads = [];
  const completedDownloads = new Set();
  let interceptMode = null;
  const heldRequests = [];
  socket.onmessage = ({ data }) => {
    const message = JSON.parse(data);
    if (message.method === 'Browser.downloadWillBegin') downloads.push(message.params);
    if (message.method === 'Browser.downloadProgress' && message.params.state === 'completed') completedDownloads.add(message.params.guid);
    if (message.method === 'Fetch.requestPaused') {
      const requestId = message.params.requestId;
      if (interceptMode === 'hold') heldRequests.push(requestId);
      else if (interceptMode !== null) {
        call('Fetch.fulfillRequest', {requestId, responseCode: 200,
          responseHeaders: [{name:'Content-Type',value:'application/json'}], body: Buffer.from(interceptMode).toString('base64')}).catch(() => {});
      } else call('Fetch.continueRequest', {requestId}).catch(() => {});
    }
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
    if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
      errors.push(message.params.args.map((arg) => arg.value || arg.description).join(' '));
    }
    if (message.id) {
      const callback = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) callback.reject(new Error(message.error.message));
      else callback.resolve(message.result);
    }
  };
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const requestId = ++id;
    pending.set(requestId, { resolve, reject });
    socket.send(JSON.stringify({ id: requestId, method, params }));
  });
  const evaluate = async (expression) => {
    const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  };
  const navigate = async path => {
    const previousPath = await evaluate('location.pathname');
    await evaluate("if (getComputedStyle(document.querySelector('nav')).display === 'none') document.querySelector('.menu-toggle').click()");
    await pause(100);
    assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display !== 'none'"), true);
    await evaluate(`document.querySelector('nav a[href="${path}"]').click()`);
    await pause(100);
    if (previousPath !== path) {
      assert.equal(await evaluate('document.activeElement === document.querySelector("h1")'), true, `${path}: focus phải đến tiêu đề trang`);
      assert.equal(await evaluate('scrollY'), 0, `${path}: vị trí cuộn phải về đầu trang`);
    }
  };
  await call('Runtime.enable');
  await call('Page.enable');
  await call('Page.bringToFront');
  const key = async (name, virtualKey, text) => {
    await call('Input.dispatchKeyEvent',{type:'keyDown',key:name,windowsVirtualKeyCode:virtualKey,...(text ? {text} : {})});
    await call('Input.dispatchKeyEvent',{type:'keyUp',key:name,windowsVirtualKeyCode:virtualKey});
    await pause(100);
  };
  const hover = async selector => {
    await evaluate(`document.querySelector('${selector}').scrollIntoView({block:'center'})`);
    await pause(80);
    const point = await evaluate(`(() => {const node=document.querySelector('${selector}');
      if(node instanceof SVGPathElement && node.closest('.recharts-pie-sector')) {
        const box=node.getBBox(),p=node.ownerSVGElement.createSVGPoint();
        for(let x=1;x<10;x++)for(let y=1;y<10;y++) {
          p.x=box.x+box.width*x/10;p.y=box.y+box.height*y/10;
          if(node.isPointInFill(p)){const screen=p.matrixTransform(node.getScreenCTM());return {x:screen.x,y:screen.y};}
        }
      }
      const rect=node.getBoundingClientRect();return {x:rect.x+rect.width/2,y:rect.y+rect.height/2};})()`);
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',...point});
    await pause(100);
    return point;
  };
  async function checkOverviewInteractions(width) {
    const assertHour = async hour => {
      const actual = await evaluate("({hour:document.querySelector('.overview-chart-readout').dataset.hour,text:document.querySelector('.overview-chart-readout').textContent,count:document.querySelectorAll('.hourly-active-bar').length})");
      assert.equal(actual.hour,String(hour));
      assert.ok(actual.text.includes(number(hourlyRows.find(row=>row.hour===hour).eventCount)));
      assert.equal(actual.count,1);
    };
    await evaluate('document.activeElement.blur()');
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
    await pause(100);
    const readoutHeight = await evaluate("document.querySelector('.overview-chart-readout').getBoundingClientRect().height");
    for (let hour=0;hour<24;hour++) {
      await hover(`.overview-hourly-panel .recharts-bar-rectangle:nth-child(${hour+1}) path`);
      await assertHour(hour);
      assert.equal(await evaluate("document.querySelector('.overview-chart-readout').getBoundingClientRect().height"),readoutHeight,'Hover không được làm dịch chuyển vùng vẽ');
    }
    const clickPoint=await hover('.overview-hourly-panel .recharts-bar-rectangle:nth-child(21) path');
    await call('Input.dispatchMouseEvent',{type:'mousePressed',...clickPoint,button:'left',clickCount:1});
    await call('Input.dispatchMouseEvent',{type:'mouseReleased',...clickPoint,button:'left',clickCount:1});
    await pause(100);
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
    await pause(100);
    await assertHour(20);
    await evaluate('document.activeElement.blur()');
    await hover('.overview-hourly-panel .recharts-bar-rectangle:nth-child(24) path');
    // Escape phải đóng cả highlight khi người dùng chỉ hover, chưa focus biểu đồ.
    await key('Escape',27);
    assert.equal(await evaluate("document.querySelectorAll('.hourly-active-bar').length"),0);
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
    await evaluate("document.querySelector('.hourly-interaction').focus()");
    await key('Home',36);
    await assertHour(0);
    for (let hour=1;hour<24;hour++) { await key('ArrowRight',39); await assertHour(hour); }
    await key('ArrowRight',39); await assertHour(23);
    await key('Home',36); await assertHour(0);
    await key('ArrowLeft',37); await assertHour(0);
    await key('End',35); await assertHour(23);
    await key('Escape',27);
    assert.equal(await evaluate("document.querySelectorAll('.hourly-active-bar').length"),0);
    assert.equal(await evaluate("document.activeElement.classList.contains('hourly-interaction')"),true);
    await evaluate("document.activeElement.blur(); document.querySelector('.hourly-interaction').focus()");
    await assertHour(23);
    await key('Tab',9);
    assert.equal(await evaluate("document.activeElement.classList.contains('hourly-interaction')"),false);
    assert.equal(await evaluate("document.querySelectorAll('.hourly-active-bar').length"),0);
    const assertAction = async action => {
      const expected=actionRows.find(row=>row.action===action);
      const actual=await evaluate("({active:document.querySelector('[data-action-slice][data-active=\"true\"]')?.dataset.actionSlice,readout:document.querySelector('.donut-selection').textContent,center:document.querySelector('.donut-center').textContent})");
      assert.equal(actual.active,action);
      assert.ok(actual.readout.includes(number(expected.count)) && actual.readout.includes(percent(expected.percentage)));
      assert.ok(actual.center.includes(percent(expected.percentage)));
    };
    await evaluate("document.querySelector('[data-action=\"play\"]').focus()");
    await key('Enter',13,'\r');
    await evaluate("document.querySelector('[data-action=\"view\"]').focus()");
    for (const row of actionRows) {
      await hover(`[data-action-slice="${row.action}"] path`);
      await assertAction(row.action);
      assert.equal(await evaluate("document.querySelector('.action-legend-item[aria-pressed=\"true\"]').dataset.action"),'play','Hover không được đổi lựa chọn đã giữ');
    }
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
    await pause(100);
    await assertAction('view');
    assert.equal(await evaluate("document.activeElement.dataset.action"),'view');
    await key('End',35); await assertAction(actionRows.at(-1).action);
    await key(' ',32);
    assert.equal(await evaluate("document.querySelector('.action-legend-item[aria-pressed=\"true\"]').dataset.action"),actionRows.at(-1).action);
    await key('Escape',27);
    assert.equal(await evaluate("document.querySelectorAll('[data-action-slice][data-active=\"true\"]').length"),0);
    await key('Home',36); await assertAction('play');
    await key('ArrowRight',39); await assertAction('view');
    await key('Tab',9);
    assert.equal(await evaluate("document.activeElement.dataset.action"),actionRows[2].action);
    // Bảng ↔ Biểu đồ giữ lựa chọn nhưng không khôi phục hover/focus đã rời đi.
    for (const mode of [2,1]) {
      await evaluate(`document.querySelector('[data-panel="actions"] .overview-view-switch button:nth-child(${mode})').focus()`);
      await key('Enter',13,'\r');
    }
    assert.equal(await evaluate("document.querySelector('.action-legend-item[aria-pressed=\"true\"]').dataset.action"),actionRows.at(-1).action);
    assert.ok((await evaluate("document.querySelector('.donut-selection').textContent")).includes(number(actionRows.at(-1).count)));
    assert.equal(await evaluate("document.querySelectorAll('[data-action-slice][data-active=\"true\"]').length"),0);
    await hover('[data-action-slice="play"] path');
    await key('Escape',27);
    assert.equal(await evaluate("document.querySelectorAll('[data-action-slice][data-active=\"true\"]').length"),0);
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
    if (width <= 390) {
      const point=await hover('.overview-hourly-panel .recharts-bar-rectangle:nth-child(21) path');
      await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
      await pause(100);
      await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{...point,radiusX:2,radiusY:2,force:1}]});
      await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
      await pause(200); await assertHour(20);
      const slicePoint=await hover('[data-action-slice="stop"] path');
      await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{...slicePoint,radiusX:2,radiusY:2,force:1}]});
      await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
      await pause(200); await assertAction('stop');
      assert.equal(await evaluate("document.querySelector('.action-legend-item[aria-pressed=\"true\"]').dataset.action"),'stop');
      await evaluate('document.activeElement.blur()');
      const dragPoint=await hover('.overview-hourly-panel .recharts-bar-rectangle:nth-child(15) path');
      await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{...dragPoint,radiusX:2,radiusY:2,force:1}]});
      for (let step=1;step<=4;step++) {
        await call('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:dragPoint.x,y:dragPoint.y-step*20,radiusX:2,radiusY:2,force:1}]});
        await pause(50);
      }
      await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
      await pause(200);
      assert.equal(await evaluate("document.activeElement.classList.contains('hourly-interaction')"),false,'Vuốt cuộn không được chọn giờ/chuyển focus');
    }
    await evaluate('document.activeElement.blur()');
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
    console.log(`Đạt: ${width}px hover 24 giờ/5 hành vi, bàn phím, Escape, focus lại, phối hợp chuột/phím và giữ lựa chọn sau đổi chế độ${width<=390?', chạm chọn giờ':''}.`);
  }
  async function checkDetailInteractions(path, width) {
    const rankingSource = path === '/phim' ? movieRows.slice(0,20) : path === '/the-loai' ? genreRows.slice(0,10)
      : path === '/ket-hop' ? combinedRows.filter(row=>row.hour===0).sort((a,b)=>a.rank-b.rank) : null;
    if (rankingSource) {
      assert.deepEqual(await evaluate("[...document.querySelectorAll('.movie-ranking h3')].map(node=>node.textContent)"),rankingSource.map(row=>row.genre ?? row.title));
      assert.deepEqual(await evaluate("[...document.querySelectorAll('.movie-rank-heading strong')].map(node=>node.textContent)"),rankingSource.map(row=>number(row.playCount)));
      for (let index=0;index<rankingSource.length;index++) {
        await evaluate(`document.querySelectorAll('.movie-ranking li')[${index}].focus()`);
        assert.equal(await evaluate(`getComputedStyle(document.querySelectorAll('.movie-rank-fill')[${index}]).backgroundColor`),'rgb(112, 81, 151)');
      }
      if (rankingSource.length>10) assert.ok(await evaluate("document.querySelector('.ranking-scroll').scrollTop > 0"),'Phải truy cập được cuối danh sách xếp hạng');
      await hover('.movie-ranking li:first-child');
      assert.equal(await evaluate("getComputedStyle(document.querySelector('.movie-rank-fill')).backgroundColor"),'rgb(112, 81, 151)');
      assert.equal(await evaluate('document.documentElement.scrollWidth>innerWidth'),false);
    }
    if (path === '/hanh-vi') {
      for (const row of actionRows) {
        await evaluate(`document.querySelector('.action-legend-item[data-action="${row.action}"]').focus()`);
        await key('Enter',13,'\r');
        const text=await evaluate("document.querySelector('.donut-selection').textContent");
        assert.ok(text.includes(number(row.count)) && text.includes(percent(row.percentage)));
        assert.equal(await evaluate("document.querySelector('[data-action-slice][data-active=\"true\"]').dataset.actionSlice"),row.action);
      }
      await key('Escape',27);
      assert.equal(await evaluate("document.querySelectorAll('[data-action-slice][data-active=\"true\"]').length"),0);
      await evaluate('document.activeElement.blur()');
      for (const row of [actionRows[0],actionRows.at(-1)]) {
        const point=await hover(`[data-action-slice="${row.action}"] path`);
        await call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
        await call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
        await pause(150);
        await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
        await pause(100);
        assert.equal(await evaluate("document.querySelector('.action-legend-item[aria-pressed=\"true\"]').dataset.action"),row.action,'Click vào lát donut phải giữ đúng lựa chọn');
        assert.equal(await evaluate("document.activeElement.dataset.action"),row.action,'Click vào lát donut chuyển focus đến tên hành động');
        assert.ok((await evaluate("document.querySelector('.donut-selection').textContent")).includes(number(row.count)));
      }
      await evaluate('document.activeElement.blur()');
    }
    if (path === '/thoi-gian') {
      await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
      await evaluate("document.querySelector('.hourly-interaction').focus()");
      await key('Home',36);
      for (let hour=0;hour<24;hour++) {
        if(hour) await key('ArrowRight',39);
        assert.equal(await evaluate("document.querySelector('.overview-chart-readout').dataset.hour"),String(hour));
        assert.ok((await evaluate("document.querySelector('.overview-chart-readout').textContent")).includes(number(hourlyRows[hour].eventCount)));
      }
      await key('Escape',27);
      assert.equal(await evaluate("document.querySelectorAll('.hourly-active-bar').length"),0);
      await evaluate('document.activeElement.blur()');
    }
    if (path === '/phan-cum') {
      const fields=['userCount','avgPlayCount','avgDistinctMovies','avgSessionCount'];
      for(let chart=0;chart<4;chart++) {
        await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
        await evaluate(`document.querySelectorAll('.comparison-interaction')[${chart}].focus()`);
        for (const [name,code,index] of [['Home',36,0],['End',35,clusterProfiles.length-1]]) {
          await key(name,code);
          const row=clusterProfiles[index];
          const readout=await evaluate(`document.querySelectorAll('.comparison-chart')[${chart}].querySelector('.overview-chart-readout').textContent`);
          assert.ok(readout.includes(`Cụm ${row.cluster}`) && readout.includes(number(row[fields[chart]])));
          assert.equal(await evaluate(`document.querySelectorAll('.comparison-chart')[${chart}].querySelectorAll('.comparison-active-bar').length`),1);
        }
        await key('Escape',27);
        assert.equal(await evaluate(`document.querySelectorAll('.comparison-chart')[${chart}].querySelectorAll('.comparison-active-bar').length`),0);
        await evaluate('document.activeElement.blur()');
        const selector=chart===0?'.cluster-size-chart':`[data-comparison="${fields[chart]}"]`;
        const point=await hover(`${selector} .recharts-bar-rectangle:nth-child(2) path`);
        await call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
        await call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
        await pause(100);
        await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
        await pause(100);
        assert.equal(await evaluate(`document.querySelectorAll('.comparison-chart')[${chart}].querySelector('.overview-chart-readout').dataset.cluster`),'1');
        await evaluate('document.activeElement.blur()');
      }
    }
    const guides=await evaluate("document.querySelectorAll('.reading-guide summary').length");
    for(let index=0;index<guides;index++) {
      await evaluate(`document.querySelectorAll('.reading-guide summary')[${index}].focus()`);
      await key('Enter',13,'\r');
      assert.equal(await evaluate(`document.querySelectorAll('.reading-guide')[${index}].open`),true);
      await key('Enter',13,'\r');
      assert.equal(await evaluate(`document.querySelectorAll('.reading-guide')[${index}].open`),false);
      assert.equal(await evaluate(`document.activeElement===document.querySelectorAll('.reading-guide summary')[${index}]`),true);
    }
    await evaluate('document.activeElement.blur()');
    console.log(`Đạt: ${width}px ${path} biểu đồ/bảng khớp JSON, highlight/focus và hướng dẫn dùng bàn phím.`);
  }
  async function checkDetailUx(path,width,downloadDirectory) {
    assert.equal(await evaluate('innerWidth'),width,'Mở bảng không được làm nở viewport mobile');
    const heights=await evaluate("[...document.querySelectorAll('.analysis-grid > .chart-panel,.analysis-grid > .daily-activity')].map(node=>node.getBoundingClientRect().height)");
    const assertHeights=async()=>{
      assert.equal(await evaluate('innerWidth'),width,'Giải thích không được làm nở viewport mobile');
      assert.deepEqual(await evaluate("[...document.querySelectorAll('.analysis-grid > .chart-panel,.analysis-grid > .daily-activity')].map(node=>node.getBoundingClientRect().height)"),heights,'Mở giải thích phải giữ nguyên chiều cao các card');
    };
    const indicators=async()=>assert.equal(await evaluate("[...document.querySelectorAll('.detail-ux details > summary')].every(s=>getComputedStyle(s,'::before').content===(s.parentElement.open?'\"▾\"':'\"▸\"') && getComputedStyle(s,'::after').content==='none')"),true,'Mũi tên phải theo đúng mục cha trực tiếp');
    const count=await evaluate("document.querySelectorAll('.analysis-explanations > details').length");
    await indicators();
    for(let i=0;i<count;i++) {
      await evaluate(`document.querySelectorAll('.analysis-explanations > details > summary')[${i}].focus()`);
      await key(i%2?' ':'Enter',i%2?32:13,i%2?' ':'\r');await pause(100);
      assert.equal(await evaluate(`document.querySelectorAll('.analysis-explanations > details')[${i}].open`),true);
      const id=await evaluate(`document.querySelectorAll('.analysis-explanations > details > summary')[${i}].getAttribute('aria-controls')`);
      assert.ok(id);
      assert.equal(await evaluate(`!!document.getElementById(${JSON.stringify(id)})?.closest('.independent-explanations')`),true);
      await assertHeights();await indicators();
      if(i%2===0) {
        await evaluate(`document.getElementById(${JSON.stringify(id)}).querySelector('.technical-definition > summary').focus()`);
        await key('Enter',13,'\r');await pause(50);await indicators();
        assert.equal(await evaluate(`document.getElementById(${JSON.stringify(id)}).querySelector('.technical-definition').open`),true);
        assert.ok((await evaluate(`document.getElementById(${JSON.stringify(id)}).textContent`)).includes(selectedSource.runId));
      }
    }
    assert.equal(await evaluate("document.querySelectorAll('.independent-explanations > .explanation-body').length"),count);
    await indicators();await assertHeights();

    const kind=({'/phim':'movies','/the-loai':'genres','/hanh-vi':'actions','/thoi-gian':'hourly'})[path];
    if(kind) {
    const csvColumns={
      movies:[['rank','Hạng'],['title','Phim'],['playCount','Lượt phát phim']],
      genres:[['rank','Hạng'],['genre','Thể loại'],['playCount','Lượt phát phim']],
      actions:[['label','Hành động'],['action','Mã hành động'],['count','Số hành động'],['percentage','Tỷ lệ hành động (%)']],
      hourly:[['label','Giờ (UTC+7)'],['eventCount','Số hành động'],['playCount','Lượt phát phim'],['distinctUsers','Người dùng duy nhất trong giờ']],
    }[kind].map(([key,label])=>({key,label}));
    const expected=(kind==='movies'?movieRows.slice(0,20):kind==='genres'?genreRows:kind==='actions'?actionRows:hourlyRows).map((row,i)=>({...row,rank:i+1,...(kind==='actions'?{label:overviewActionLabels[row.action]}:kind==='hourly'?{label:`${String(row.hour).padStart(2,'0')}h`}:{})}));
    async function download(expectedRows) {
      const start=downloads.length;
      await evaluate("document.querySelector('.analysis-results .csv-button').focus()");await key('Enter',13,'\r');
      for(let i=0;i<40;i++){if(downloads.length>start&&completedDownloads.has(downloads.at(-1).guid))break;await pause(100);}
      assert.ok(downloads.length>start&&completedDownloads.has(downloads.at(-1).guid),'CSV phải tải thành công');
      assert.equal(downloads.at(-1).suggestedFilename,`phan-tich-${kind}.csv`);
      assert.equal(await readFile(new URL(downloads.at(-1).guid,downloadDirectory),'utf8'),buildCsv(csvColumns,expectedRows));
    }
    await download(expected);
    if(kind==='movies') {
      await evaluate("document.querySelector('.page-size select').value='10';document.querySelector('.page-size select').dispatchEvent(new Event('change',{bubbles:true}))");await pause(100);
      assert.equal(await evaluate("document.querySelectorAll('.analysis-results tbody tr').length"),10);
      await evaluate("document.querySelector('.results-pagination button:last-child').focus()");await key('Enter',13,'\r');await pause(100);
      assert.deepEqual(await evaluate("[...document.querySelectorAll('.analysis-results tbody tr')].map(row=>row.children[1].textContent)"),expected.slice(10).map(row=>row.title));
      await download(expected); // CSV giữ tất cả kết quả, kể cả khi ở trang 2.
      const query=async value=>{await evaluate(`(()=>{const input=document.querySelector('.analysis-results input[type=search]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,${JSON.stringify(value)});input.dispatchEvent(new Event('input',{bubbles:true}));})()`);await pause(100);};
      await query(expected.at(-1).title.toUpperCase());
      assert.equal(await evaluate("document.querySelector('.analysis-results tbody tr td').textContent"),String(expected.length));
      await download([expected.at(-1)]);
      await query('khong-co-phim-xyz');
      assert.equal(await evaluate("document.querySelectorAll('.analysis-results tbody tr').length"),0);
      assert.equal(await evaluate("document.querySelector('.analysis-results .csv-button').disabled"),true);
      await query('');
      await evaluate("document.querySelector('.page-size select').value='20';document.querySelector('.page-size select').dispatchEvent(new Event('change',{bubbles:true}))");await pause(100);
      assert.equal(await evaluate("document.querySelectorAll('.analysis-results tbody tr').length"),expected.length);
    }
    } else await checkAdvancedCsv(path,downloadDirectory);
    for(let i=0;i<count;i++) {
      const id=await evaluate(`document.querySelectorAll('.analysis-explanations > details > summary')[${i}].getAttribute('aria-controls')`);
      await evaluate(`document.getElementById(${JSON.stringify(id)}).querySelector('.explanation-close').focus()`);await key('Enter',13,'\r');await pause(80);
      assert.equal(await evaluate(`document.activeElement===document.querySelectorAll('.analysis-explanations > details > summary')[${i}]`),true);
      assert.equal(await evaluate(`document.querySelectorAll('.analysis-explanations > details')[${i}].open`),false);
      await indicators();
    }
    // Mở/đóng lặp bằng cả Enter và Space, giữ nguyên vùng vẽ và trạng thái.
    for(let repeat=0;repeat<2;repeat++)for(const [name,code,text] of [['Enter',13,'\r'],[' ',32,' ']]){
      await evaluate("document.querySelector('.analysis-explanations > details > summary').focus()");await key(name,code,text);await pause(80);await indicators();await assertHeights();
    }
    assert.equal(await evaluate("document.querySelectorAll('.independent-explanations > .explanation-body').length"),0);
    assert.ok(await evaluate("document.querySelectorAll('.analysis-related a[href]').length>=2"));
    assert.equal(await evaluate('document.documentElement.scrollWidth>innerWidth'),false);
    console.log(`Đạt: ${width}px ${path} giải thích độc lập/lồng nhau, Enter/Space, trả focus, CSV khớp JSON${kind==='movies'?', tìm kiếm/phân trang/CSV giữ hạng gốc':''}.`);
  }
  async function checkAdvancedCsv(path,downloadDirectory) {
    const query=async(selector,value)=>{
      await evaluate(`(()=>{const input=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,${JSON.stringify(value)});input.dispatchEvent(new Event('input',{bubbles:true}));})()`);await pause(100);
    };
    const select=async(selector,value)=>{await evaluate(`document.querySelector(${JSON.stringify(selector)}).value=${JSON.stringify(String(value))};document.querySelector(${JSON.stringify(selector)}).dispatchEvent(new Event('change',{bubbles:true}))`);await pause(100);};
    async function download(filename,columns,rows) {
      const start=downloads.length;
      await evaluate(`document.querySelector('[data-export="${filename}"]').focus()`);await key('Enter',13,'\r');
      for(let i=0;i<40;i++){if(downloads.length>start&&completedDownloads.has(downloads.at(-1).guid))break;await pause(100);}
      assert.ok(downloads.length>start&&completedDownloads.has(downloads.at(-1).guid),'CSV phải tải thành công');
      assert.equal(downloads.at(-1).suggestedFilename,filename);
      assert.equal(await readFile(new URL(downloads.at(-1).guid,downloadDirectory),'utf8'),buildCsv(columns,rows),'CSV phải giữ giá trị gốc đúng phạm vi đã lọc');
    }
    if(path==='/thoi-luong') {
      const columns=[{key:'scope',label:'Nhóm bản ghi'},{key:'unit',label:'Đơn vị gốc'},...durationFields.map(row=>({key:row.key,label:`${row.label} (${row.unit})`}))];
      await download('thong-ke-thoi-luong.csv',columns,['all_events','watch_segments'].map(scope=>durationRows.find(row=>row.scope===scope)));
      await evaluate("document.querySelector('[data-chart=watch-duration] .comparison-interaction').focus()");
      for(const [name,code,scope] of [['Home',36,'all_events'],['End',35,'watch_segments']]) {
        await key(name,code);
        assert.ok((await evaluate("document.querySelector('[data-chart=watch-duration] .overview-chart-readout').textContent")).includes(number(durationRows.find(row=>row.scope===scope).mean)));
      }
      await key('Escape',27);await evaluate('document.activeElement.blur()');
    }
    if(path==='/ket-hop') {
      const columns=[['hour','Giờ UTC+7'],['rank','Hạng trong giờ'],['movieId','Mã phim'],['title','Phim'],['playCount','Lượt phát phim'],['distinctUsers','Người dùng duy nhất trong nhóm']].map(([key,label])=>({key,label}));
      await download('phim-theo-gio.csv',columns,combinedRows);
      await select('#combined-page-size',12);
      await evaluate("document.querySelector('.results-pagination button:last-child').focus()");await key('Enter',13,'\r');
      assert.deepEqual(await evaluate("[...document.querySelectorAll('.combined-browse tbody tr')].map(row=>[row.children[0].textContent,row.children[2].textContent])"),combinedRows.slice(12,24).map(row=>[`${String(row.hour).padStart(2,'0')}h`,row.title]));
      await download('phim-theo-gio.csv',columns,combinedRows);
      await query('#combined-query',combinedRows[0].title.toUpperCase());
      const matching=combinedRows.filter(row=>row.title.toLowerCase().includes(combinedRows[0].title.toLowerCase()));
      await download('phim-theo-gio.csv',columns,matching);
      await evaluate("document.querySelector('#combined-only-selected').click()");await pause(100);
      await download('phim-theo-gio.csv',columns,matching.filter(row=>row.hour===0));
      await query('#combined-query','khong-co-phim-xyz');
      assert.equal(await evaluate("document.querySelectorAll('.combined-browse tbody tr').length"),0);
      assert.equal(await evaluate("document.querySelector('[data-export]').disabled"),true);
      await query('#combined-query','');await evaluate("document.querySelector('#combined-only-selected').click()");await select('#combined-page-size',0);
    }
    if(path==='/phan-cum') {
      const columns=[['userId','Mã người dùng'],['cluster','Mã cụm'],['playCount','Lượt phát phim'],['completeCount','Hành động hoàn thành xem phim'],['distinctMovies','Phim khác nhau'],['distinctGenres','Thể loại khác nhau'],['sessionCount','Phiên sử dụng'],['playedSessionCount','Phiên có phát phim'],['completedSessionCount','Phiên có hoàn thành'],['completionRate','Tỷ lệ hoàn thành phiên (0–1)'],['completionRateDefined','Tỷ lệ có xác định'],['totalWatchDuration','Tổng thời lượng (giây)'],['avgWatchDuration','Trung bình đoạn xem (giây)']].map(([key,label])=>({key,label}));
      await download('nguoi-dung-theo-cum.csv',columns,clusterUsers);
      await evaluate("document.querySelector('.cluster-pagination button:last-child').focus()");await key('Enter',13,'\r');
      await download('nguoi-dung-theo-cum.csv',columns,clusterUsers);
      await query('#cluster-user-query',clusterUsers.at(-1).userId);
      await download('nguoi-dung-theo-cum.csv',columns,[clusterUsers.at(-1)]);
      await query('#cluster-user-query','');await select('#cluster-user-filter',clusterProfiles[0].cluster);
      await download('nguoi-dung-theo-cum.csv',columns,clusterUsers.filter(row=>row.cluster===clusterProfiles[0].cluster));
      await query('#cluster-user-query','khong-co-user-xyz');
      assert.equal(await evaluate("document.querySelector('[data-export]').disabled"),true);
      await query('#cluster-user-query','');await select('#cluster-user-filter','all');
      assert.ok((await evaluate("document.querySelector('.independent-explanations').textContent")).includes(String(clusteringMetadata.seed)));
      assert.deepEqual(await evaluate("[...document.querySelectorAll('.feature-list code')].map(node=>node.textContent)"),JSON.parse(clusteringMetadata.featureColumnsJson));
    }
  }
  const routes = [
    ['/', 'Tổng quan hoạt động xem phim', 0], ['/phim', 'Phân tích phim', 20],
    ['/hanh-vi', 'Hành vi người dùng', 5], ['/thoi-gian', 'Hoạt động theo thời gian', 24 + dailyRows.length],
    ['/the-loai', 'Phân tích thể loại', 20],
    ['/thoi-luong', 'Thời lượng xem', 6],
    ['/ket-hop', 'Phân tích kết hợp', 75],
    ['/phan-cum', 'Phân nhóm người dùng', 31],
  ];
  const selectedWidth = Number(process.argv.find(arg => arg.startsWith('--width='))?.split('=')[1]);
  const selectedRoute = process.argv.find(arg => arg.startsWith('--route='))?.split('=')[1];
  const includedRoutes = process.argv.includes('--advanced-pages') ? routes.filter(([path])=>['/thoi-luong','/ket-hop','/phan-cum'].includes(path)) : process.argv.includes('--detail-pages') ? routes.filter(([path])=>['/phim','/the-loai','/hanh-vi','/thoi-gian'].includes(path)) : selectedRoute ? routes.filter(([path])=>path===selectedRoute) : routes;
  assert.ok(!selectedWidth || [1440,768,390,320].includes(selectedWidth), 'Kích thước kiểm tra không được hỗ trợ');
  assert.ok(!selectedRoute || routes.some(([path]) => path === selectedRoute), 'Route kiểm tra không được hỗ trợ');
  for (const width of selectedWidth ? [selectedWidth] : [1440, 768, 390, 320]) {
    const downloadDirectory = new URL(`downloads-${width}/`, artifacts);
    await mkdir(downloadDirectory, {recursive:true});
    await call('Browser.setDownloadBehavior', {behavior:'allowAndName',downloadPath:fileURLToPath(downloadDirectory),eventsEnabled:true});
    await call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width <= 390 });
    await call('Emulation.setTouchEmulationEnabled', {enabled: width <= 390, maxTouchPoints: 1});
    for (const [path, title, rows] of includedRoutes) {
      await call('Page.navigate', { url: origin + path });
      let ready = false;
      for (let attempt = 0; attempt < 150; attempt++) {
        const expectedBars = path === '/' || path === '/thoi-gian' ? 24 : path === '/phan-cum' ? clusterProfiles.length * 4 : path === '/thoi-luong' ? 2 : 0;
        const expectedRanking = path === '/' ? 5 : path === '/phim' ? 20 : path === '/the-loai' ? 10 : path === '/ket-hop' ? 3 : 0;
        ready = await evaluate(`!!document.querySelector('${path === '/' ? '.metrics-grid' : 'tbody'}') && document.querySelectorAll('.recharts-bar-rectangle').length === ${expectedBars} && document.querySelectorAll('.movie-ranking li').length === ${expectedRanking} ${path === '/' || path === '/hanh-vi' ? "&& document.querySelectorAll('.recharts-pie-sector').length === 5" : ''}`);
        if (ready) break;
        await pause(100);
      }
      assert.ok(ready, `${width}px ${path}: không tải được dữ liệu`);
      await pause(500);
      const result = await evaluate(`({
        title: document.querySelector('h1')?.textContent,
        rows: document.querySelectorAll('tbody tr').length,
        charts: document.querySelectorAll('.recharts-wrapper > .recharts-surface').length,
        rankingBars: document.querySelectorAll('.movie-ranking li').length,
        overflow: document.documentElement.scrollWidth > innerWidth,
        kpis: [...document.querySelectorAll('.metric-value')].map(node => node.textContent),
        links: [...document.querySelectorAll('.detail-link')].map(node => node.getAttribute('href')),
        text: document.querySelector('main').textContent
      })`);
      assert.equal(result.title, title);
      assert.equal(result.rows, rows);
      assert.equal(result.charts, path === '/' ? 2 : path === '/phan-cum' ? 4 : path === '/thoi-gian' ? 2 : path === '/hanh-vi' || path === '/thoi-luong' ? 1 : 0);
      assert.equal(await evaluate("!!document.querySelector('.overview-heading .overview-scope')"),true,'Tám trang phải dùng phạm vi dữ liệu thống nhất');
      assert.equal(result.overflow, false, `${width}px ${path}: trang bị tràn ngang`);
      assert.ok(result.text.includes(selectedSource.runId),'Dashboard phải hiển thị đúng run đã xác minh');
      if (path === '/thoi-gian') {
        const actualDaily = await evaluate("[...document.querySelectorAll('.daily-activity tbody tr')].map(row=>[row.children[0].textContent,row.children[1].textContent])");
        assert.deepEqual(actualDaily,dailyRows.map(row=>[row.date.split('-').reverse().join('/'),number(row.activeUsers)]));
        assert.equal(await evaluate("document.querySelectorAll('.daily-chart .recharts-line-dot').length"),dailyRows.length);
        await evaluate("document.querySelector('.daily-chart .comparison-interaction').focus()");
        await key('End',35);
        assert.ok(await evaluate("document.querySelector('.daily-chart .overview-chart-readout').textContent.includes('" + dailyRows.at(-1).date.split('-').reverse().join('/') + "')"));
        await key('Home',36);
        assert.ok(await evaluate("document.querySelector('.daily-chart .overview-chart-readout').textContent.includes('" + dailyRows[0].date.split('-').reverse().join('/') + "')"));
        await evaluate('document.activeElement.blur()');
        await evaluate("document.querySelector('.daily-chart').scrollIntoView({block:'center'})");
        await pause(300);
        const dailyScreenshot = await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        await writeFile(new URL(`${width}-daily-chart.png`,artifacts),Buffer.from(dailyScreenshot.data,'base64'));
        await evaluate("document.querySelector('.daily-activity .table-shell').closest('details').open=true");
        await pause(200);
      }
      if (path === '/thoi-luong') {
        for (const metric of ['mean','median','min','max','stddev']) {
          await evaluate(`document.querySelector('#duration-stat').value='${metric}'; document.querySelector('#duration-stat').dispatchEvent(new Event('change',{bubbles:true}))`);
          await pause(200);
          assert.equal(await evaluate("document.querySelector('[data-chart=\"watch-duration\"]').dataset.statistic"),metric);
          const labels = await evaluate("[...document.querySelectorAll('[data-chart=\"watch-duration\"] .recharts-label-list text')].map(node=>node.textContent)");
          // Recharts omits labels for zero-width bars; the visible value key must
          // still state both numbers, including zero, without inventing a bar.
          const scopes = ['all_events','watch_segments'];
          assert.deepEqual(labels,scopes.map(scope=>durationRows.find(row=>row.scope===scope)[metric]).filter(value=>value!==0).map(number));
          const values = await evaluate("[...document.querySelectorAll('[data-duration-scope] strong')].map(node=>node.textContent)");
          assert.deepEqual(values,scopes.map(scope=>number(durationRows.find(row=>row.scope===scope)[metric])+' giây'));
        }
        await evaluate("document.querySelector('#duration-stat').value='mean'; document.querySelector('#duration-stat').dispatchEvent(new Event('change',{bubbles:true}))");
        await pause(200);
        await evaluate("document.querySelector('[data-chart=\"watch-duration\"]').closest('.chart-panel').scrollIntoView({block:'center'})");
        const durationScreenshot = await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        await writeFile(new URL(`${width}-duration-chart.png`,artifacts),Buffer.from(durationScreenshot.data,'base64'));
      }
      assert.equal(await evaluate("document.querySelectorAll('nav a').length"), 8);
      assert.equal(await evaluate("document.querySelector('nav a[aria-current=\"page\"]').getAttribute('href')"), path);
      if (width <= 1023) {
        assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'none');
        await evaluate("document.querySelector('.menu-toggle').click()");
        await pause(100);
        assert.equal(await evaluate("document.querySelector('.menu-toggle').getAttribute('aria-expanded')"), 'true');
        assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'flex');
        if (path === '/') {
          const menuScreenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
          await writeFile(new URL(`${width}-menu.png`, artifacts), Buffer.from(menuScreenshot.data, 'base64'));
        }
        await evaluate("document.querySelector('nav a').focus({preventScroll:true})");
        await call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
        await call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
        await pause(100);
        assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'none');
        assert.equal(await evaluate("document.activeElement === document.querySelector('.menu-toggle')"), true);
        await evaluate("document.querySelector('.menu-toggle').click(); document.querySelector('nav a[aria-current=\"page\"]').click()");
        await pause(100);
        assert.equal(await evaluate("document.activeElement === document.querySelector('.menu-toggle')"), true);
      } else {
        assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'flex');
        assert.equal(await evaluate("document.querySelector('.app-header').getBoundingClientRect().right <= document.querySelector('main').getBoundingClientRect().left"), true);
      }
      const tables = await evaluate("[...document.querySelectorAll('.table-scroll')].map(node => ({overflow:node.scrollWidth>node.clientWidth+1,hint:!!document.getElementById(node.getAttribute('aria-describedby')),label:node.getAttribute('aria-label')}))");
      for (let index = 0; index < tables.length; index++) {
        assert.ok(tables[index].label);
        assert.equal(tables[index].hint, tables[index].overflow);
        if (!tables[index].overflow) continue;
        await evaluate(`document.querySelectorAll('.table-scroll')[${index}].focus({preventScroll:true})`);
        for (const [key, code] of [['ArrowRight',39], ['End',35], ['Home',36]]) {
          await call('Input.dispatchKeyEvent', {type:'keyDown',key,windowsVirtualKeyCode:code});
          await call('Input.dispatchKeyEvent', {type:'keyUp',key,windowsVirtualKeyCode:code});
          const position = await evaluate(`document.querySelectorAll('.table-scroll')[${index}].scrollLeft`);
          if (key === 'Home') assert.equal(position,0);
          else assert.ok(position>0, `${path}: không cuộn bảng bằng ${key}`);
        }
        for (const modifier of ['altKey','ctrlKey','metaKey']) {
          assert.equal(await evaluate(`document.querySelectorAll('.table-scroll')[${index}].dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowLeft',${modifier}:true,bubbles:true,cancelable:true}))`), true, `${path}: không được chặn phím tắt trình duyệt`);
        }
        if (width <= 390) {
          await evaluate(`document.querySelectorAll('.table-scroll')[${index}].scrollIntoView({block:'center'})`);
          const point = await evaluate(`(() => { const rect = document.querySelectorAll('.table-scroll')[${index}].getBoundingClientRect(); return {x:rect.left+rect.width*0.8,y:Math.max(120,Math.min(850,rect.top+rect.height/2))}; })()`);
          await call('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[{...point,id:1}]});
          for (let step=1;step<=6;step++) {
            await pause(40);
            await call('Input.dispatchTouchEvent', {type:'touchMove',touchPoints:[{x:point.x-step*25,y:point.y,id:1}]});
          }
          await call('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
          await pause(300);
          assert.ok(await evaluate(`document.querySelectorAll('.table-scroll')[${index}].scrollLeft > 0`), `${path}: không cuộn ngang bảng bằng cảm ứng mô phỏng`);
          await evaluate(`document.querySelectorAll('.table-scroll')[${index}].scrollLeft=0; window.scrollTo(0,0)`);
        }
      }
      if (width <= 560) assert.ok(await evaluate(`[...document.querySelectorAll('.metric-card')].every(node => node.getBoundingClientRect().height <= ${path === '/' ? 260 : 200} && node.scrollWidth <= node.clientWidth+1)`), `${path}: KPI mobile quá cao hoặc cắt nội dung`);
      if (path === '/') {
        assert.deepEqual(result.kpis, expectedKpis);
        assert.deepEqual(result.links, ['/thoi-gian', '/hanh-vi', '/phim']);
        const peak = Math.max(...hourlyRows.map(row => row.eventCount));
        const readHighlight = key => evaluate(`document.querySelector('[data-highlight="${key}"]').textContent`);
        assert.ok((await readHighlight('movie')).includes(movieRows[0].title));
        assert.ok((await readHighlight('movie')).includes(number(movieRows[0].playCount)));
        assert.ok((await readHighlight('action')).includes(number(actionRows[0].count)));
        assert.ok((await readHighlight('action')).includes(percent(actionRows[0].percentage)));
        assert.ok((await readHighlight('hour')).includes(number(peak)));
        for (const row of hourlyRows.filter(row => row.eventCount === peak)) assert.ok((await readHighlight('hour')).includes(hourRange(row.hour)));
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.highlight-card a')].map(node=>node.getAttribute('href'))"), ['/phim','/hanh-vi','/thoi-gian']);
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.action-legend-item strong')].map(node=>node.textContent)"), actionRows.map(row=>percent(row.percentage)));
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.movie-rank-heading strong')].map(node=>node.textContent)"), movieRows.slice(0,5).map(row=>number(row.playCount)));
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.movie-ranking h3')].map(node=>node.textContent)"), movieRows.slice(0,5).map(row=>row.title));
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.recharts-wrapper')[0].querySelectorAll('.recharts-bar-rectangle path')].map(node=>node.getAttribute('fill'))"), hourlyRows.map(row=>row.eventCount===peak?'#244c78':'#698cae'));
        // Lớp chính không bắt người xem đọc mã trường hoặc file; các phần sâu mở bằng bàn phím.
        assert.equal(await evaluate("/\\.json|tv2-|playCount|sessionCount/.test(document.querySelector('.overview-home').innerText)"),false);
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.metrics-grid h2')].map(node=>node.textContent)"),['Tổng số hành động','Số người dùng','Lượt phát phim']);
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.action-count')].map(node=>node.textContent)"),actionRows.map(row=>number(row.count)+' lần'));
        const assertDisclosureIndicators = async () => {
          const problems=await evaluate(`Array.from(document.querySelectorAll('.overview-home details > summary')).filter(summary=>
            !getComputedStyle(summary,'::before').content.includes(summary.parentElement.open?'▾':'▸')
            || getComputedStyle(summary,'::after').content!=='none'
            || getComputedStyle(summary).listStyleType!=='none').map(node=>node.textContent)`);
          assert.deepEqual(problems,[],'Mỗi summary chỉ có một mũi tên theo trạng thái của chính details');
        };
        const toggleWithKeyboard = async selector => {
          await evaluate(`document.querySelector('${selector} > summary').focus()`);
          await key('Enter',13,'\r');
          assert.equal(await evaluate(`document.querySelector('${selector}').open`),true);
          assert.equal(await evaluate('document.documentElement.scrollWidth>innerWidth'),false);
          await assertDisclosureIndicators();
          const contentId = await evaluate(`document.querySelector('${selector} > summary').getAttribute('aria-controls')`);
          return contentId ? `[id="${contentId}"]` : selector;
        };
        const closeWithKeyboard = async selector => {
          await evaluate(`document.querySelector('${selector} > summary').focus()`);
          await key(' ',32);
          assert.equal(await evaluate(`document.querySelector('${selector}').open`),false);
          assert.equal(await evaluate(`document.activeElement===document.querySelector('${selector} > summary')`),true);
          await assertDisclosureIndicators();
        };
        await assertDisclosureIndicators();
        const kpiHeights = await evaluate("[...document.querySelectorAll('.metrics-grid > .metric-card')].map(node=>node.getBoundingClientRect().height)");
        const assertKpiHeights = async () => assert.deepEqual(await evaluate("[...document.querySelectorAll('.metrics-grid > .metric-card')].map(node=>node.getBoundingClientRect().height)"),kpiHeights,'Mở giải thích không được tăng chiều cao card KPI');
        for (let index=1;index<=3;index++) {
          const selector=`.metrics-grid .metric-card:nth-child(${index}) .metric-explanation`;
          const content = await toggleWithKeyboard(selector);
          assert.ok(await evaluate(`document.querySelector('${content}').textContent.includes('Cách tính:')`));
          await assertKpiHeights();
          await toggleWithKeyboard(content+' .technical-definition');
          assert.ok(await evaluate(`document.querySelector('${content} .technical-definition').textContent.includes('.json')`));
          await assertKpiHeights();
          await closeWithKeyboard(content+' .technical-definition');
          await closeWithKeyboard(selector);
        }
        const firstKpi='.metrics-grid .metric-card:first-child .metric-explanation';
        for(let index=1;index<=3;index++) await toggleWithKeyboard(`.metrics-grid .metric-card:nth-child(${index}) .metric-explanation`);
        await assertKpiHeights();
        assert.equal(await evaluate("document.querySelectorAll('.overview-home > .independent-explanations > section').length"),3);
        const firstRegion = await evaluate("document.querySelector('.metrics-grid .metric-explanation > summary').getAttribute('aria-controls')");
        await evaluate(`document.getElementById('${firstRegion}').querySelector('.explanation-close').click()`);
        assert.equal(await evaluate(`document.querySelector('${firstKpi}').open`),false);
        assert.equal(await evaluate(`document.activeElement===document.querySelector('${firstKpi} > summary')`),true);
        assert.equal(await evaluate("document.querySelectorAll('.metrics-grid .metric-explanation[open]').length"),2);
        for(let index=2;index<=3;index++) await closeWithKeyboard(`.metrics-grid .metric-card:nth-child(${index}) .metric-explanation`);
        for(let repeat=0;repeat<3;repeat++) { await toggleWithKeyboard(firstKpi);await closeWithKeyboard(firstKpi); }
        // Bấm chuột thật vào summary, không chỉ gán thuộc tính open bằng script.
        for(const expected of [true,false]) {
          const point=await hover(firstKpi+' > summary');
          await call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
          await call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
          await pause(150);
          assert.equal(await evaluate(`document.querySelector('${firstKpi}').open`),expected);
          await assertDisclosureIndicators();
        }
        await assertKpiHeights();
        assert.equal(await evaluate("document.querySelector('.overview-home > .independent-explanations').children.length"),0);
        await toggleWithKeyboard('.overview-sessions');
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.session-value')].map(node=>node.textContent)"),[overview.totalSessions,overview.playedSessions].map(number));
        for (let index=1;index<=2;index++) {
          const selector=`.session-grid article:nth-child(${index}) .metric-explanation`;
          const content = await toggleWithKeyboard(selector);
          await toggleWithKeyboard(content+' .technical-definition');
          await closeWithKeyboard(content+' .technical-definition');
          await closeWithKeyboard(selector);
        }
        await closeWithKeyboard('.overview-sessions');
        await toggleWithKeyboard('.overview-source');
        assert.ok(await evaluate("document.querySelector('.overview-source').textContent.includes('stats_action_distribution.json')"));
        assert.ok(await evaluate("document.querySelector('.overview-source').textContent.includes('Flume') && document.querySelector('.overview-source').textContent.includes('HDFS') && document.querySelector('.overview-source').textContent.includes('Spark')"));
        await closeWithKeyboard('.overview-source');
        const accessibilityProblems = await evaluate(`(() => {
          const problems=[], ids=[...document.querySelectorAll('[id]')].map(node=>node.id);
          if(new Set(ids).size!==ids.length) problems.push('Trùng id');
          for(const node of document.querySelectorAll('.overview-home [aria-describedby],.overview-home [aria-controls]')) {
            for(const attr of ['aria-describedby','aria-controls']) for(const id of (node.getAttribute(attr)||'').split(' ').filter(Boolean)) {
              if(!document.getElementById(id)) problems.push('Thiếu đích '+id);
            }
          }
          for(const node of document.querySelectorAll('.overview-home button,.overview-home a,.overview-home summary')) {
            if(!(node.getAttribute('aria-label')||node.textContent).trim()) problems.push('Thiếu tên điều khiển');
          }
          return problems;
        })()`);
        assert.deepEqual(accessibilityProblems,[],'Liên kết aria, id và tên điều khiển phải hợp lệ');
        assert.equal(await evaluate("document.querySelector('.overview-comparison-link')"),null);
        const actionLabels = overviewActionLabels;
        for (const row of actionRows) {
          await evaluate(`document.querySelector('[data-action="${row.action}"]').focus()`);
          await call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});
          await call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
          await pause(150);
          const selection = await evaluate("document.querySelector('.donut-selection').textContent");
          assert.ok(selection.includes(number(row.count)) && selection.includes(percent(row.percentage)), `Chọn ${row.action}: ${selection}`);
          assert.equal(await evaluate("document.querySelector('[data-action-slice][data-active=\"true\"]').getAttribute('data-action-slice')"),row.action);
          assert.equal(await evaluate("document.querySelectorAll('[data-action-slice][data-active=\"true\"]').length"),1);
        }
        for (let index=0;index<5;index++) {
          await evaluate(`document.querySelectorAll('.movie-ranking li')[${index}].focus()`);
          assert.equal(await evaluate(`getComputedStyle(document.querySelectorAll('.movie-ranking li')[${index}].querySelector('.movie-rank-fill')).backgroundColor`),'rgb(112, 81, 151)');
        }
        const expectedDatasets = {
          hourly: hourlyRows.map(row => ({...row,label:`${String(row.hour).padStart(2,'0')}h`})),
          actions: actionRows.map(row=>({...row,label:actionLabels[row.action]})),
          movies: movieRows.slice(0,5).map((row,index)=>({...row,rank:index+1})),
        };
        const chartHeights=await evaluate("['hourly','actions'].map(kind=>document.querySelector('[data-panel='+kind+']').getBoundingClientRect().height)");
        const assertChartHeights=async()=>assert.deepEqual(await evaluate("['hourly','actions'].map(kind=>document.querySelector('[data-panel='+kind+']').getBoundingClientRect().height)"),chartHeights,'Nội dung mở rộng không được kéo cao hàng card biểu đồ');
        const hourlyHelp='[data-panel="hourly"] .overview-help:not(.operation-help)';
        const actionsHelp='[data-panel="actions"] .overview-help:not(.operation-help)';
        const hourlyContent=await toggleWithKeyboard(hourlyHelp);
        await assertChartHeights();
        await toggleWithKeyboard(actionsHelp);
        await toggleWithKeyboard(hourlyContent+' .technical-definition');
        await assertChartHeights();
        await closeWithKeyboard(hourlyContent+' .technical-definition');
        await closeWithKeyboard(hourlyHelp);
        assert.equal(await evaluate(`document.querySelector('${actionsHelp}').open`),true);
        await closeWithKeyboard(actionsHelp);
        await assertChartHeights();
        if(width===1440) {
          const sideBySide=await evaluate("(() => { const chart=document.querySelector('.donut-visual').getBoundingClientRect(),legend=document.querySelector('.action-legend').getBoundingClientRect();return chart.right<=legend.left+1 && chart.width>=190 && chart.height>=200; })()");
          assert.ok(sideBySide,'Desktop: donut và chú giải phải cạnh nhau, giữ biểu đồ đủ lớn');
        }
        for (const kind of ['hourly','actions','movies']) {
          const helpSelector=`[data-panel="${kind}"] .overview-help:not(.operation-help)`;
          const content=await toggleWithKeyboard(helpSelector);
          await toggleWithKeyboard(content+' .technical-definition');
          await toggleWithKeyboard(`[data-panel="${kind}"] .operation-help`);
          await evaluate(`document.querySelector('[data-panel="${kind}"] .overview-view-switch button:nth-child(2)').focus()`);
          await call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});
          await call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
          await pause(200);
          const config = overviewTables[kind];
          assert.deepEqual(await evaluate(`[...document.querySelectorAll('[data-panel="${kind}"] tbody tr')].map(row=>[...row.children].map(cell=>cell.textContent))`), expectedDatasets[kind].map(row=>config.columns.filter(column=>column.key!=='action').map(column=>column.format==='number'?number(row[column.key]):column.format==='percent'?percent(row[column.key]):String(row[column.key]))));
          assert.equal(await evaluate('document.documentElement.scrollWidth > innerWidth'),false);
          const downloadCount = downloads.length;
          await evaluate(`document.querySelector('[data-panel="${kind}"] .csv-button').click()`);
          for (let attempt=0;attempt<100;attempt++) {
            if (downloads.length>downloadCount && completedDownloads.has(downloads.at(-1).guid)) break;
            await pause(100);
          }
          assert.ok(downloads.length>downloadCount && completedDownloads.has(downloads.at(-1).guid),'CSV không được tải xuống');
          assert.equal(downloads.at(-1).suggestedFilename,config.filename);
          assert.equal(await readFile(new URL(downloads.at(-1).guid,downloadDirectory),'utf8'),buildCsv(config.columns,expectedDatasets[kind]));
          if (kind === 'hourly' && await evaluate("document.querySelector('[data-panel=\"hourly\"] .table-scroll').scrollWidth <= document.querySelector('[data-panel=\"hourly\"] .table-scroll').clientWidth + 1")) {
            await evaluate("document.querySelector('[data-panel=\"hourly\"] .table-scroll').focus()");
            await key('End',35); await pause(400);
            assert.ok(await evaluate("document.querySelector('[data-panel=\"hourly\"] .table-scroll').scrollTop > 0"),'End phải cuộn xuống bảng giờ');
            await key('Home',36); await pause(400);
            assert.equal(await evaluate("document.querySelector('[data-panel=\"hourly\"] .table-scroll').scrollTop"),0);
          }
          await closeWithKeyboard(content+' .technical-definition');
          await closeWithKeyboard(helpSelector);
          await closeWithKeyboard(`[data-panel="${kind}"] .operation-help`);
          await evaluate(`document.querySelector('[data-panel="${kind}"] .overview-view-switch button:first-child').click()`);
          await pause(300);
        }
        console.log(`Đạt: ${width}px donut chọn bằng bàn phím; bảng và 3 CSV tải xuống khớp đúng 24/5/5 dòng JSON.`);
        await checkOverviewInteractions(width);
      }
      if (path === '/' || path === '/phim') assert.ok(result.text.includes('Catch That Kid'));
      const readTable = (selector = 'tbody tr') => evaluate(`[...document.querySelectorAll('${selector}')].map(row => [...row.children].map(cell => cell.textContent))`);
      if (path === '/phim') assert.deepEqual(await readTable(), movieRows.slice(0,20).map((row,index) => [String(index+1),row.title,number(row.playCount)]));
      if (path === '/hanh-vi') assert.deepEqual(await readTable(), actionRows.map(row => [overviewActionLabels[row.action],number(row.count),percent(row.percentage)]));
      if (path === '/thoi-gian') {
        assert.deepEqual(await readTable('.analysis-wide tbody tr'), hourlyRows.map(row => [`${String(row.hour).padStart(2,'0')}h`,number(row.eventCount),number(row.playCount),number(row.distinctUsers)]));
        assert.ok(result.text.includes('Mỗi ngày có 1.000 người dùng hoạt động'));
        assert.ok(result.text.includes('30 ngày'));
      }
      if (path === '/the-loai') assert.deepEqual(await readTable(), genreRows.map((row,index) => [String(index+1),row.genre,number(row.playCount)]));
      if (path === '/phan-cum') {
        assert.equal(await evaluate("document.querySelector('.clustering-page .metric-card h2').textContent"), 'Người dùng được phân nhóm');
        assert.equal(await evaluate("document.querySelector('.clustering-page .metric-value').textContent"), number(clusteringMetadata.users));
        assert.equal(await evaluate("document.querySelector('.selected-k th').textContent"), String(clusteringMetadata.bestK));
        assert.equal(await evaluate("document.querySelector('.selected-k td').title"), String(clusteringMetadata.silhouette));
        await evaluate("document.querySelector('summary[aria-label=\"Giải thích dữ liệu: K-Means và Silhouette\"]').parentElement.open=true");await pause(100);
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.feature-list code')].map(node => node.textContent)"), JSON.parse(clusteringMetadata.featureColumnsJson));
        await evaluate("document.querySelector('summary[aria-label=\"Giải thích dữ liệu: K-Means và Silhouette\"]').parentElement.open=false");await pause(100);
        assert.deepEqual(await evaluate("[...document.querySelector('.cluster-size-summary').parentElement.querySelectorAll('.recharts-label-list text')].map(node => node.textContent)"), clusterProfiles.map(row => number(row.userCount)));
        for (const key of ['avgPlayCount', 'avgDistinctMovies', 'avgSessionCount']) {
          assert.deepEqual(await evaluate(`[...document.querySelector('[data-comparison="${key}"]').querySelectorAll('.recharts-label-list text')].map(node => node.textContent)`), clusterProfiles.map(row => number(row[key])));
        }
        assert.equal(await evaluate("document.querySelector('.user-lookup').scrollWidth > document.querySelector('.user-lookup').clientWidth"), true);
        assert.ok(await evaluate("document.querySelector('#user-scroll-help').textContent.includes('10 cột')"));
        await evaluate("document.querySelector('.user-lookup').scrollLeft = document.querySelector('.user-lookup').scrollWidth");
        assert.ok(await evaluate("document.querySelector('.user-lookup').scrollLeft > 0"));
        await evaluate("document.querySelector('.user-lookup').scrollLeft = 0");
        const profileTable = await evaluate("[...document.querySelectorAll('.cluster-profile-table tbody tr')].map(row => ({key: row.dataset.profile, cells: [...row.querySelectorAll('td')].map(cell => ({text: cell.textContent, raw: cell.title}))}))");
        for (const row of profileTable) assert.deepEqual(row.cells, clusterProfiles.map(profile => ({text: row.key === 'avgCompletionRate' ? percent(profile[row.key]*100) : number(profile[row.key]), raw: String(profile[row.key])})));
        const visibleIds = () => evaluate("[...document.querySelectorAll('.user-lookup tbody th')].map(node => node.textContent)");
        assert.deepEqual(await visibleIds(), clusterUsers.slice(0,20).map(row => row.userId));
        await evaluate("[...document.querySelectorAll('.cluster-pagination button')].find(node => node.textContent === 'Trang sau').click()");
        await pause(150);
        assert.deepEqual(await visibleIds(), clusterUsers.slice(20,40).map(row => row.userId));
        const query = async value => {
          await evaluate(`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(document.querySelector('#cluster-user-query'),${JSON.stringify(value)}); document.querySelector('#cluster-user-query').dispatchEvent(new Event('input',{bubbles:true}))`);
          await pause(150);
        };
        await query(clusterUsers[0].userId);
        assert.deepEqual(await visibleIds(), [clusterUsers[0].userId]);
        await query('sim-user-0000');
        assert.deepEqual(await visibleIds(), clusterUsers.filter(row => row.userId.includes('sim-user-0000')).slice(0,20).map(row => row.userId));
        await evaluate("document.querySelector('#cluster-user-filter').value = '0'; document.querySelector('#cluster-user-filter').dispatchEvent(new Event('change',{bubbles:true}))");
        await pause(150);
        assert.deepEqual(await visibleIds(), clusterUsers.filter(row => row.cluster === 0 && row.userId.includes('sim-user-0000')).slice(0,20).map(row => row.userId));
        await query('khong-co-user');
        assert.deepEqual(await visibleIds(), []);
        assert.ok(await evaluate("document.querySelector('.user-lookup').closest('.chart-panel').textContent.includes('Không tìm thấy')"));
        await query('');
        for (const profile of clusterProfiles) {
          await evaluate(`document.querySelector('#cluster-user-filter').value = '${profile.cluster}'; document.querySelector('#cluster-user-filter').dispatchEvent(new Event('change',{bubbles:true}))`);
          await pause(150);
          assert.ok(await evaluate(`document.querySelector('.lookup-status').textContent.includes('${number(profile.userCount)} người dùng')`));
          assert.deepEqual(await visibleIds(), clusterUsers.filter(row => row.cluster === profile.cluster).slice(0,20).map(row => row.userId));
        }
        await evaluate("document.querySelector('#cluster-user-filter').value = 'all'; document.querySelector('#cluster-user-filter').dispatchEvent(new Event('change',{bubbles:true}))");
        await pause(150);
        console.log(`Đạt: ${width}px metadata/hồ sơ, tỷ lệ %, tìm userId, lọc cụm, phân trang và kết quả tìm trống.`);
      }
      if (path === '/ket-hop') {
        const formatted = (data) => data.map(row => [
          `${String(row.hour).padStart(2, '0')}h`, String(row.rank), row.title,
          new Intl.NumberFormat('vi-VN').format(row.playCount), new Intl.NumberFormat('vi-VN').format(row.distinctUsers),
        ]);
        assert.equal(await evaluate("document.querySelectorAll('#combined-hour option').length"), 24);
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.combined-browse tbody tr')].map(row => [...row.children].map(cell => cell.textContent))"), formatted(combinedRows));
        await evaluate("document.querySelector('#combined-only-selected').click()");
        for (let hour = 0; hour < 24; hour++) {
          await evaluate(`document.querySelector('#combined-hour').value = '${hour}'; document.querySelector('#combined-hour').dispatchEvent(new Event('change', { bubbles: true }))`);
          await pause(100);
          const expected = combinedRows.filter(row => row.hour === hour).sort((a,b) => a.rank - b.rank);
          const selected = await evaluate("[...document.querySelectorAll('.combined-selected tbody tr')].map(row => [...row.children].map(cell => cell.textContent))");
          const filtered = await evaluate("[...document.querySelectorAll('.combined-browse tbody tr')].map(row => [...row.children].map(cell => cell.textContent))");
          assert.deepEqual(selected, formatted(expected));
          assert.deepEqual(filtered, formatted(expected));
          assert.deepEqual(await evaluate("[...document.querySelectorAll('.movie-rank-heading strong')].map(node => node.textContent)"), expected.map(row => number(row.playCount)));
          assert.deepEqual(await evaluate("[...document.querySelectorAll('.ranking-users')].map(node => node.textContent)"), expected.map(row => number(row.distinctUsers) + ' người dùng khác nhau trong nhóm phim–giờ'));
          const observation = await evaluate("document.querySelector('.combined-observation').textContent");
          assert.ok(observation.includes(expected[0].title));
          assert.ok(observation.includes(new Intl.NumberFormat('vi-VN').format(expected[0].playCount - expected[1].playCount)));
        }
        await evaluate("document.querySelector('#combined-only-selected').click(); document.querySelector('#combined-hour').value = '0'; document.querySelector('#combined-hour').dispatchEvent(new Event('change', { bubbles: true }))");
        await pause(200);
        assert.equal(await evaluate("document.querySelectorAll('.combined-browse tbody tr').length"), 72);
        console.log(`Đạt: ${width}px đổi đủ 24 giờ; biểu đồ, hai bảng, người dùng và nhận xét khớp JSON.`);
      }
      if (path === '/thoi-luong') {
        const all = durationRows.find(row => row.scope === 'all_events');
        const segments = durationRows.find(row => row.scope === 'watch_segments');
        const actual = await evaluate("[...document.querySelectorAll('tbody tr')].map(row => ({key: row.dataset.stat, values: [...row.querySelectorAll('td')].map(cell => ({text: cell.textContent, raw: cell.title}))}))");
        const expected = ['count', 'mean', 'median', 'min', 'max', 'stddev'].map(key => ({key, values: [all, segments].map(row => ({text: new Intl.NumberFormat('vi-VN').format(row[key]), raw: String(row[key])}))}));
        assert.deepEqual(actual, expected);
        assert.ok(result.text.includes('Đơn vị: giây'));
        assert.ok(result.text.includes('2.727,425 giây'));
        console.log(`Đạt: ${width}px đối chiếu đủ 12 giá trị thời lượng, định dạng giây và nhận xét với JSON.`);
      }
      if (path === '/the-loai') {
        assert.equal(await evaluate("document.querySelector('#genre-limit').value"), '10');
        assert.deepEqual(await evaluate("[...document.querySelectorAll('tbody tr')].slice(0,2).map(row => [...row.children].map(cell => cell.textContent))"), [
          ['1', 'Comedy', '144.882'], ['2', 'Drama', '143.222'],
        ]);
        assert.ok(result.text.includes('1.660'));
        for (const [limit, expected] of [['5', 5], ['all', 20], ['10', 10]]) {
          await evaluate(`document.querySelector('#genre-limit').value = '${limit}'; document.querySelector('#genre-limit').dispatchEvent(new Event('change', { bubbles: true }))`);
          await pause(300);
          assert.equal(await evaluate("document.querySelectorAll('.movie-ranking li').length"), expected);
          assert.deepEqual(await evaluate("[...document.querySelectorAll('.movie-ranking h3')].map(node=>node.textContent)"),genreRows.slice(0,expected).map(row=>row.genre));
          assert.deepEqual(await evaluate("[...document.querySelectorAll('.movie-rank-heading strong')].map(node=>node.textContent)"),genreRows.slice(0,expected).map(row=>number(row.playCount)));
          assert.equal(await evaluate("document.querySelectorAll('tbody tr').length"), 20);
        }
        console.log(`Đạt: ${width}px chọn Top 5/10/toàn bộ; nhận xét và bảng thể loại khớp JSON.`);
      }
      if (path !== '/') await checkDetailInteractions(path,width);
      if (path !== '/') await checkDetailUx(path,width,downloadDirectory);
      const tooltipValues = path === '/' ? [number(hourlyRows[0].eventCount),number(actionRows[0].count)]
        : path === '/hanh-vi' ? [percent(actionRows[0].percentage)]
        : path === '/thoi-gian' ? [number(hourlyRows[0].eventCount)]
        : path === '/phan-cum' ? [number(clusterProfiles[0].userCount),...['avgPlayCount','avgDistinctMovies','avgSessionCount'].map(key => number(clusterProfiles[0][key]))] : [];
      for (let chartIndex = 0; chartIndex < tooltipValues.length; chartIndex++) {
        const pie = (path === '/' && chartIndex === 1) || path === '/hanh-vi';
        const shape = pie ? '.recharts-pie-sector path' : '.recharts-bar-rectangle';
        await evaluate(`document.querySelectorAll('.recharts-wrapper')[${chartIndex}].querySelector('${shape}').scrollIntoView({block:'center'})`);
        await pause(200);
        const point = await evaluate(`(() => {const node=document.querySelectorAll('.recharts-wrapper')[${chartIndex}].querySelector('${shape}');
          if (${pie}) {const box=node.getBBox();const p=node.ownerSVGElement.createSVGPoint();for(let x=1;x<10;x++)for(let y=1;y<10;y++){p.x=box.x+box.width*x/10;p.y=box.y+box.height*y/10;if(node.isPointInFill(p)){const screen=p.matrixTransform(node.getScreenCTM());return {x:screen.x,y:screen.y};}}}
          const rect=node.getBoundingClientRect();return {x:rect.x+rect.width/2,y:rect.y+rect.height/2};})()`);
        await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:point.x,y:point.y});
        await pause(200);
        const tooltip = path === '/phan-cum' ? await evaluate(`(() => {const node=document.querySelectorAll('.comparison-chart')[${chartIndex}].querySelector('.overview-chart-readout');return {visible:node.dataset.cluster==='0',text:node.textContent};})()`)
          : await evaluate(`(() => {const node=document.querySelector('${pie ? '.donut-selection' : '.overview-chart-readout'}');return {visible:${pie ? "node?.dataset.action === 'play'" : "node?.dataset.hour === '0'"},text:node?.textContent};})()`);
        if(!tooltip.visible) {
          console.log('Hover diagnostic:',{point,tooltip,layout:await evaluate(`({viewport:{width:innerWidth,height:innerHeight,scale:visualViewport.scale},focus:document.activeElement?.outerHTML,hit:document.elementFromPoint(${point.x},${point.y})?.outerHTML,rect:document.querySelector('.hourly-interaction')?.getBoundingClientRect().toJSON(),chart:document.querySelector('.chart-frame .recharts-wrapper')?.getBoundingClientRect().toJSON()})`)});
          const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
          await writeFile(new URL(`${width}-${path.slice(1)}-hover-debug.png`,artifacts),Buffer.from(shot.data,'base64'));
        }
        assert.equal(tooltip.visible,true,`${width}px ${path}: vùng đọc số liệu không hiển thị đúng nhóm`);
        assert.ok(tooltip.text.includes(tooltipValues[chartIndex]),`${path}: tooltip ${tooltip.text} không khớp ${tooltipValues[chartIndex]}`);
        if (path === '/' && chartIndex === 0) assert.ok(tooltip.text.includes('UTC+7') && await evaluate("document.querySelector('.hourly-interaction').getAttribute('aria-label').includes('toàn kỳ')"));
        if (path === '/' && chartIndex === 0) {
          assert.equal(await evaluate("document.querySelector('.hourly-active-bar')?.getAttribute('fill')"),'#315fa8');
          assert.equal(await evaluate("document.querySelector('.hourly-active-bar')?.getAttribute('stroke-width')"),'2');
        }
        if (path === '/' && chartIndex === 1) {
          assert.equal(await evaluate("document.querySelector('[data-action-slice][data-active=\"true\"]').getAttribute('data-action-slice')"),actionRows[0].action);
          assert.ok(await evaluate("getComputedStyle(document.querySelector('.donut-sector.is-active')).filter !== 'none'"));
        }
        const tooltipOverflow = await evaluate('document.documentElement.scrollWidth > innerWidth');
        if (tooltipOverflow) {
          console.log('Overflow diagnostic:', await evaluate("[...document.querySelectorAll('.recharts-tooltip-wrapper,.recharts-default-tooltip,.recharts-tooltip-item')].map(node=>({className:node.className,rect:node.getBoundingClientRect().toJSON(),whiteSpace:getComputedStyle(node).whiteSpace,text:node.textContent}))"));
          const debugScreenshot = await call('Page.captureScreenshot', {format:'png',captureBeyondViewport:false});
          await writeFile(new URL(`${width}-tooltip-debug.png`,artifacts),Buffer.from(debugScreenshot.data,'base64'));
        }
        assert.equal(tooltipOverflow, false, `${path}: tooltip gây tràn ngang`);
        if (path === '/') {
          const screenshot = await call('Page.captureScreenshot', {format:'png',captureBeyondViewport:false});
          await writeFile(new URL(`${width}-overview-chart-${chartIndex}.png`,artifacts),Buffer.from(screenshot.data,'base64'));
        }
      }
      await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
      if (path === '/') {
        await pause(150);
        assert.equal(await evaluate("document.querySelectorAll('[data-action-slice][data-active=\"true\"]').length"),0);
        await evaluate("document.querySelector('.hourly-interaction').focus()");
        await call('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowRight',code:'ArrowRight',windowsVirtualKeyCode:39});
        await call('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowRight',code:'ArrowRight',windowsVirtualKeyCode:39});
        await pause(150);
        assert.equal(await evaluate("document.querySelector('.hourly-active-bar')?.getAttribute('fill')"),'#315fa8');
        await evaluate('document.activeElement.blur()');
        await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
      }
      if (result.charts > 0) {
        await evaluate("window.scrollTo(0,window.scrollY+document.querySelector('.chart-frame,.donut-visual').getBoundingClientRect().top-160)");
        await pause(500);
        const chartScreenshot = await call('Page.captureScreenshot', {format:'png',captureBeyondViewport:false});
        await writeFile(new URL(`${width}-${path.slice(1) || 'overview'}-chart.png`, artifacts), Buffer.from(chartScreenshot.data,'base64'));
      }
      if (path === '/thoi-gian') await evaluate("document.querySelector('.daily-activity .table-shell').closest('details').open=false");
      await evaluate('window.scrollTo(0,0)');
      const fullHeight = await evaluate('document.documentElement.scrollHeight');
      const screenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip:{x:0,y:0,width,height:fullHeight,scale:1} });
      await writeFile(new URL(`${width}-${path.slice(1) || 'overview'}.png`, artifacts), Buffer.from(screenshot.data, 'base64'));
      await call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width <= 390 });
      if (path !== '/') {
        // Chỉ chụp full-page sau tất cả tương tác: Edge có thể tạm thay visual viewport.
        await pause(200);
        await evaluate("document.querySelectorAll('.analysis-explanations > details').forEach(node=>node.open=true)");await pause(100);
        await evaluate("document.querySelectorAll('.independent-explanations .technical-definition').forEach(node=>node.open=true);window.scrollTo(0,0)");await pause(100);
        const expandedHeight=await evaluate('document.documentElement.scrollHeight');
        const expanded=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:expandedHeight,scale:1}});
        await writeFile(new URL(`${width}-${path.slice(1)}-explanations-open.png`,artifacts),Buffer.from(expanded.data,'base64'));
        await evaluate("document.querySelectorAll('.analysis-explanations > details').forEach(node=>node.open=false)");
        await call('Emulation.setDeviceMetricsOverride', {width,height:1000,deviceScaleFactor:1,mobile:width<=390});await pause(200);
      }
      if (path === '/phan-cum') {
        await evaluate("document.querySelector('.cluster-comparisons').scrollIntoView({block:'start'})");
        await pause(600);
        const comparisonScreenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
        await writeFile(new URL(`${width}-cluster-comparison.png`, artifacts), Buffer.from(comparisonScreenshot.data, 'base64'));
        await evaluate('window.scrollTo(0,0)');
      }
      console.log(`Đạt: ${width}px ${path}, ${result.charts} biểu đồ SVG, ${result.rankingBars} thanh xếp hạng HTML, ${rows} dòng bảng, không tràn trang.`);
    }
    // Điều hướng bằng liên kết thực, sau đó quay lại bằng lịch sử trình duyệt.
    await navigate('/');
    await pause(200);
    await evaluate("document.querySelector('.detail-link[href=\"/phim\"]').click()");
    await pause(200);
    assert.equal(await evaluate('location.pathname'), '/phim');
    await evaluate('history.back()');
    await pause(200);
    assert.equal(await evaluate('location.pathname'), '/');
    await navigate('/the-loai');
    await pause(300);
    assert.equal(await evaluate('location.pathname'), '/the-loai');
    assert.equal(await evaluate("document.querySelector('h1').textContent"), 'Phân tích thể loại');
    await navigate('/thoi-luong');
    await pause(300);
    assert.equal(await evaluate('location.pathname'), '/thoi-luong');
    assert.equal(await evaluate("document.querySelector('h1').textContent"), 'Thời lượng xem');
    await navigate('/ket-hop');
    await pause(300);
    assert.equal(await evaluate('location.pathname'), '/ket-hop');
    assert.equal(await evaluate("document.querySelector('h1').textContent"), 'Phân tích kết hợp');
    await navigate('/phan-cum');
    await pause(300);
    assert.equal(await evaluate('location.pathname'), '/phan-cum');
    assert.equal(await evaluate("document.querySelector('h1').textContent"), 'Phân nhóm người dùng');
    if (width <= 1023) assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'none');
    // Chuyển từ trang dài sau khi cuộn, rồi kiểm tra cả tám liên kết.
    await navigate('/phim');
    await evaluate('window.scrollTo(0,800)');
    for (const [path] of routes) await navigate(path);
    await evaluate("document.querySelector('.skip-link').focus(); document.querySelector('.skip-link').click()");
    assert.equal(await evaluate("document.activeElement.id"), 'main-content');
    await navigate('/');
    await call('Page.navigate',{url:origin+'/?layout=v1'});
    for(let attempt=0;attempt<150;attempt++) { if(await evaluate("document.querySelectorAll('.metric-value').length === 3 && document.querySelectorAll('.highlight-card').length === 3")) break; await pause(100); }
    assert.equal(await evaluate("document.querySelectorAll('.overview-comparison-link,.overview-version-switch,.summary-grid').length"),0,'URL cũ không được khôi phục giao diện V1');
    assert.deepEqual(await evaluate("[...document.querySelectorAll('.metric-value')].map(node=>node.textContent)"), expectedKpis);
    assert.equal(await evaluate("document.querySelectorAll('.highlight-card').length"),3);
    // Kiểm tra tất cả liên kết phân tích mới bằng điều hướng thật.
    for (const selector of ['.highlight-card a','.overview-page .detail-link']) {
      for (let index=0;index<3;index++) {
        const href = await evaluate(`document.querySelectorAll('${selector}')[${index}].getAttribute('href')`);
        await evaluate(`document.querySelectorAll('${selector}')[${index}].click()`);
        await pause(250);
        assert.equal(await evaluate('location.pathname'),href);
        await navigate('/');
      }
    }
    console.log(`Đạt: ${width}px menu 8 chức năng, trạng thái trang hiện tại và mở/đóng menu mobile.`);
  }
  const faultRoutes = [
    ['/', 'stats_action_distribution.json'], ['/phim','stats_action_distribution.json'], ['/hanh-vi','stats_action_distribution.json'],
    ['/thoi-gian','stats_daily_active_users.json'], ['/the-loai','stats_top_genres.json'],
    ['/thoi-luong','stats_watch_duration_summary.json'], ['/ket-hop','stats_user_movie_time.json'], ['/phan-cum','kmeans_model_metadata.json'],
  ];
  const waitFor = async expression => {
    for(let attempt=0;attempt<150;attempt++) { if(await evaluate(expression)) return; await pause(100); }
    throw new Error(`Hết thời gian chờ: ${expression}`);
  };
  for (const [path,file] of faultRoutes.filter(([path]) => includedRoutes.some(([route])=>route===path))) {
    await call('Fetch.enable',{patterns:[{urlPattern:`*/data/*/${file}`,requestStage:'Request'}]});
    interceptMode='hold';
    heldRequests.length=0;
    await call('Page.navigate',{url:origin+path});
    await waitFor("!!document.querySelector('.status-panel[role=\"status\"]')");
    await pause(200);
    assert.ok(heldRequests.length>0);
    interceptMode='[]';
    await Promise.allSettled(heldRequests.splice(0).map(requestId => call('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from('[]').toString('base64')})));
    await waitFor("!!document.querySelector('[role=\"alert\"]')");
    assert.equal(await evaluate("document.querySelector('[role=\"alert\"] h2').textContent"),'Thiếu dữ liệu');
    interceptMode='{broken';
    await evaluate("document.querySelector('[role=\"alert\"] button').click()");
    await waitFor("document.querySelector('[role=\"alert\"] h2')?.textContent==='Không thể đọc dữ liệu'");
    assert.ok(await evaluate("document.querySelector('[role=\"alert\"]').textContent.includes('JSON không hợp lệ')"));
    interceptMode=null;
    await call('Fetch.disable');
    await evaluate("document.querySelector('[role=\"alert\"] button').click()");
    await waitFor("!document.querySelector('[role=\"alert\"]') && !document.querySelector('.status-panel[role=\"status\"]')");
    console.log(`Đạt: ${path} tải chậm → dữ liệu trống → JSON hỏng → thử lại thành công.`);
  }
  await call('Page.navigate', { url: origin + '/khong-ton-tai' });
  await waitFor("document.querySelector('h1')?.textContent==='Không tìm thấy trang'");
  assert.equal(await evaluate("document.querySelector('h1')?.textContent"), 'Không tìm thấy trang');
  assert.deepEqual(errors, [], 'Có lỗi JavaScript/React trong trình duyệt');
  await writeFile(new URL('result.json',artifacts),JSON.stringify({status:'PASS',runId:selectedSource.runId,
    checkedAt:new Date().toISOString(),widths:selectedWidth?[selectedWidth]:[1440,768,390,320],
    routes:includedRoutes.map(row=>row[0]),javascriptErrors:errors},null,2));
  console.log('Browser artifacts:',fileURLToPath(artifacts));
  console.log('Đạt: liên kết chi tiết, Back, trang không tồn tại và không có lỗi JavaScript/React.');
} finally {
  socket?.close();
  browser.kill();
  await vite.close();
}
