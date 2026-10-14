// Kiểm tra giao diện bằng Edge có sẵn và CDP, không cần thư viện trình duyệt.
import { spawn } from 'node:child_process';
import { createServer as createNetServer } from 'node:net';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import assert from 'node:assert/strict';
import { number, percent } from '../src/services/formatNumbers.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const sourceData = async name => JSON.parse(await readFile(new URL(`../public/data/${name}`, import.meta.url), 'utf8'));
const actionRows = (await sourceData('stats_action_distribution.json')).sort((a,b) => b.count-a.count);
const hourlyRows = await sourceData('stats_hourly_activity.json');
const movieRows = await sourceData('stats_top_movies_by_play.json');
const genreRows = await sourceData('stats_top_genres.json');
const durationRows = JSON.parse(await readFile(new URL('../public/data/stats_watch_duration_summary.json', import.meta.url), 'utf8'));
const combinedRows = JSON.parse(await readFile(new URL('../public/data/stats_user_movie_time.json', import.meta.url), 'utf8'));
const clusteringMetadata = JSON.parse(await readFile(new URL('../public/data/kmeans_model_metadata.json', import.meta.url), 'utf8'))[0];
const clusterProfiles = JSON.parse(await readFile(new URL('../public/data/kmeans_cluster_profiles.json', import.meta.url), 'utf8'));
const clusterUsers = JSON.parse(await readFile(new URL('../public/data/kmeans_assignments.json', import.meta.url), 'utf8')).sort((a,b) => a.userId.localeCompare(b.userId));
const artifacts = new URL('../.browser-check/', import.meta.url);
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
  let interceptMode = null;
  const heldRequests = [];
  socket.onmessage = ({ data }) => {
    const message = JSON.parse(data);
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
    const result = await call('Runtime.evaluate', { expression, returnByValue: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  };
  const navigate = async path => {
    await evaluate("if (getComputedStyle(document.querySelector('nav')).display === 'none') document.querySelector('.menu-toggle').click()");
    await pause(100);
    assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display !== 'none'"), true);
    await evaluate(`document.querySelector('nav a[href="${path}"]').click()`);
  };
  await call('Runtime.enable');
  await call('Page.enable');
  const routes = [
    ['/', 'Tổng quan', 0], ['/phim', 'Phân tích phim', 20],
    ['/hanh-vi', 'Hành vi người dùng', 5], ['/thoi-gian', 'Hoạt động theo thời gian', 24],
    ['/the-loai', 'Phân tích thể loại', 20],
    ['/thoi-luong', 'Thời lượng xem', 6],
    ['/ket-hop', 'Phân tích kết hợp', 75],
    ['/phan-cum', 'Phân cụm người dùng', 31],
  ];
  for (const width of [1440, 900, 390, 320]) {
    await call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
    for (const [path, title, rows] of routes) {
      await call('Page.navigate', { url: origin + path });
      let ready = false;
      for (let attempt = 0; attempt < 150; attempt++) {
        const expectedBars = path === '/' ? 34 : path === '/the-loai' ? 10 : path === '/thoi-luong' ? 0 : path === '/ket-hop' ? 3 : path === '/phan-cum' ? clusterProfiles.length * 4 : rows;
        ready = await evaluate(`!!document.querySelector('${path === '/' ? '.metrics-grid' : 'tbody'}') && document.querySelectorAll('.recharts-bar-rectangle').length === ${expectedBars}`);
        if (ready) break;
        await pause(100);
      }
      assert.ok(ready, `${width}px ${path}: không tải được dữ liệu`);
      await pause(500);
      const result = await evaluate(`({
        title: document.querySelector('h1')?.textContent,
        rows: document.querySelectorAll('tbody tr').length,
        charts: document.querySelectorAll('.recharts-wrapper > .recharts-surface').length,
        overflow: document.documentElement.scrollWidth > innerWidth,
        kpis: [...document.querySelectorAll('.metric-value')].map(node => node.textContent),
        links: [...document.querySelectorAll('.detail-link')].map(node => node.getAttribute('href')),
        text: document.querySelector('main').textContent
      })`);
      assert.equal(result.title, title);
      assert.equal(result.rows, rows);
      assert.equal(result.charts, path === '/' ? 3 : path === '/thoi-luong' ? 0 : path === '/phan-cum' ? 4 : 1);
      assert.equal(result.overflow, false, `${width}px ${path}: trang bị tràn ngang`);
      assert.equal(await evaluate("document.querySelectorAll('nav a').length"), 8);
      assert.equal(await evaluate("document.querySelector('nav a[aria-current=\"page\"]').getAttribute('href')"), path);
      if (width <= 760) {
        assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'none');
        await evaluate("document.querySelector('.menu-toggle').click()");
        await pause(100);
        assert.equal(await evaluate("document.querySelector('.menu-toggle').getAttribute('aria-expanded')"), 'true');
        assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'flex');
        if (path === '/') {
          const menuScreenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
          await writeFile(new URL('390-menu.png', artifacts), Buffer.from(menuScreenshot.data, 'base64'));
        }
        await evaluate("document.querySelector('.menu-toggle').click()");
        await pause(100);
        assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'none');
      } else {
        assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'flex');
        assert.equal(await evaluate("document.querySelector('.app-header').getBoundingClientRect().right <= document.querySelector('main').getBoundingClientRect().left"), true);
      }
      if (path === '/') {
        assert.deepEqual(result.kpis, ['1.000.000', '1.000', '303.052', '257.928']);
        assert.deepEqual(result.links, ['/hanh-vi', '/thoi-gian', '/phim']);
      }
      if (path === '/' || path === '/phim') assert.ok(result.text.includes('Catch That Kid'));
      const readTable = () => evaluate("[...document.querySelectorAll('tbody tr')].map(row => [...row.children].map(cell => cell.textContent))");
      if (path === '/phim') assert.deepEqual(await readTable(), movieRows.slice(0,20).map((row,index) => [String(index+1),row.title,number(row.playCount)]));
      if (path === '/hanh-vi') assert.deepEqual(await readTable(), actionRows.map(row => [`${({play:'Phát phim',view:'Xem thông tin',pause:'Tạm dừng',stop:'Dừng phát',complete:'Hoàn thành'})[row.action]} (${row.action})`,number(row.count),percent(row.percentage)]));
      if (path === '/thoi-gian') {
        assert.deepEqual(await readTable(), hourlyRows.map(row => [`${String(row.hour).padStart(2,'0')}h`,number(row.eventCount),number(row.playCount),number(row.distinctUsers)]));
        assert.ok(result.text.includes('Mỗi ngày có 1.000 người dùng hoạt động'));
        assert.ok(result.text.includes('30 ngày'));
      }
      if (path === '/the-loai') assert.deepEqual(await readTable(), genreRows.map((row,index) => [String(index+1),row.genre,number(row.playCount)]));
      if (path === '/phan-cum') {
        assert.equal(await evaluate("document.querySelector('.clustering-page .metric-card h2').textContent"), 'Người dùng được phân cụm');
        assert.equal(await evaluate("document.querySelector('.clustering-page .metric-value').textContent"), number(clusteringMetadata.users));
        assert.equal(await evaluate("document.querySelector('.selected-k th').textContent"), String(clusteringMetadata.bestK));
        assert.equal(await evaluate("document.querySelector('.selected-k td').title"), String(clusteringMetadata.silhouette));
        assert.deepEqual(await evaluate("[...document.querySelectorAll('.feature-list code')].map(node => node.textContent)"), JSON.parse(clusteringMetadata.featureColumnsJson));
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
        assert.ok(await evaluate("document.querySelector('.user-lookup').parentElement.textContent.includes('Không tìm thấy')"));
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
          assert.deepEqual(await evaluate("[...document.querySelectorAll('.recharts-label-list text')].map(node => node.textContent)"), expected.map(row => new Intl.NumberFormat('vi-VN').format(row.playCount)));
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
        assert.ok(result.text.includes('Đơn vị gốc: giây'));
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
          assert.equal(await evaluate("document.querySelectorAll('.recharts-bar-rectangle').length"), expected);
          assert.equal(await evaluate("document.querySelectorAll('tbody tr').length"), 20);
        }
        console.log(`Đạt: ${width}px chọn Top 5/10/toàn bộ; nhận xét và bảng thể loại khớp JSON.`);
      }
      const tooltipValues = path === '/' ? [percent(actionRows[0].percentage),number(hourlyRows[0].eventCount),number(movieRows[0].playCount)]
        : path === '/phim' ? [number(movieRows[0].playCount)] : path === '/hanh-vi' ? [percent(actionRows[0].percentage)]
        : path === '/thoi-gian' ? [number(hourlyRows[0].eventCount)] : path === '/the-loai' ? [number(genreRows[0].playCount)]
        : path === '/ket-hop' ? [number(combinedRows[0].playCount)]
        : path === '/phan-cum' ? [number(clusterProfiles[0].userCount),...['avgPlayCount','avgDistinctMovies','avgSessionCount'].map(key => number(clusterProfiles[0][key]))] : [];
      for (let chartIndex = 0; chartIndex < tooltipValues.length; chartIndex++) {
        await evaluate(`document.querySelectorAll('.recharts-wrapper')[${chartIndex}].querySelector('.recharts-bar-rectangle').scrollIntoView({block:'center'})`);
        await pause(200);
        const point = await evaluate(`(() => {const node=document.querySelectorAll('.recharts-wrapper')[${chartIndex}].querySelector('.recharts-bar-rectangle');const rect=node.getBoundingClientRect();return {x:rect.x+rect.width/2,y:rect.y+rect.height/2};})()`);
        await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:point.x,y:point.y});
        await pause(200);
        const tooltip = await evaluate(`(() => {const node=document.querySelectorAll('.recharts-wrapper')[${chartIndex}].querySelector('.recharts-tooltip-wrapper');return {visible:node && getComputedStyle(node).visibility==='visible',text:node?.textContent};})()`);
        assert.equal(tooltip.visible,true,`${width}px ${path}: tooltip không hiển thị`);
        assert.ok(tooltip.text.includes(tooltipValues[chartIndex]),`${path}: tooltip ${tooltip.text} không khớp ${tooltipValues[chartIndex]}`);
      }
      await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
      await evaluate('window.scrollTo(0,0)');
      const fullHeight = await evaluate('document.documentElement.scrollHeight');
      await call('Emulation.setDeviceMetricsOverride', { width, height: fullHeight, deviceScaleFactor: 1, mobile: false });
      await pause(700);
      const screenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
      await writeFile(new URL(`${width}-${path.slice(1) || 'overview'}.png`, artifacts), Buffer.from(screenshot.data, 'base64'));
      await call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
      if (path === '/phan-cum') {
        await evaluate("document.querySelector('.cluster-comparisons').scrollIntoView({block:'start'})");
        await pause(600);
        const comparisonScreenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
        await writeFile(new URL(`${width}-cluster-comparison.png`, artifacts), Buffer.from(comparisonScreenshot.data, 'base64'));
        await evaluate('window.scrollTo(0,0)');
      }
      console.log(`Đạt: ${width}px ${path}, ${result.charts} biểu đồ, ${rows} dòng bảng, không tràn trang.`);
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
    assert.equal(await evaluate("document.querySelector('h1').textContent"), 'Phân cụm người dùng');
    if (width <= 760) assert.equal(await evaluate("getComputedStyle(document.querySelector('nav')).display"), 'none');
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
  for (const [path,file] of faultRoutes) {
    await call('Fetch.enable',{patterns:[{urlPattern:`*/data/${file}`,requestStage:'Request'}]});
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
  await pause(300);
  assert.equal(await evaluate("document.querySelector('h1')?.textContent"), 'Không tìm thấy trang');
  assert.deepEqual(errors, [], 'Có lỗi JavaScript/React trong trình duyệt');
  console.log('Đạt: liên kết chi tiết, Back, trang không tồn tại và không có lỗi JavaScript/React.');
} finally {
  socket?.close();
  browser.kill();
  await vite.close();
}
