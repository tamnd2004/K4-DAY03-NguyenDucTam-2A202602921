"use strict";
const paths = {
  sparkles:'<path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4L12 3Z"/><path d="M20 2v4m-2-2h4"/>',
  building:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h1m4 0h1M9 11h1m4 0h1M9 15h1m4 0h1M10 21v-3h4v3"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 11h18m-13 5h3m3 0h2"/>',
  book:'<path d="M12 5C9 3 5 3 2 4v15c3-1 7-1 10 1m0-15c3-2 7-2 10-1v15c-3-1-7-1-10 1V5Z"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
  leaf:'<path d="M20 3c-11-1-17 4-15 11 2 7 14 5 15-11Z"/><path d="M4 21 15 9"/>',
  code:'<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 16"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  'arrow-right':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  'arrow-up':'<path d="M12 20V4m-6 6 6-6 6 6"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  link:'<path d="m10 14 4-4m-6 7-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2-1 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(1 0)"/>',
  shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  route:'<circle cx="6" cy="5" r="2"/><circle cx="18" cy="19" r="2"/><path d="M8 5h8a4 4 0 0 1 0 8H8a3 3 0 0 0 0 6h8"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
  activity:'<path d="M2 12h4l3-8 6 16 3-8h4"/>',
  message:'<path d="M21 11a8 8 0 0 1-8 8H5l-3 3V11a9 9 0 0 1 19 0Z"/><path d="M7 10h10m-10 4h6"/>',
  database:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  x:'<path d="m6 6 12 12M6 18 18 6"/>',
};
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
function icon(name) {return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.sparkles}</svg>`;}
function fillIcons(root=document) {root.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=icon(el.dataset.icon);});}
const escapeHTML = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatAnswer = text => escapeHTML(text).replace(/\*\*([^\n*]+)\*\*/g,'<strong>$1</strong>').replace(/`([^\n`]+)`/g,'<code>$1</code>').replace(/^\s*[-*]\s+/gm,'• ');
const dateVN = s => s.split('-').reverse().join('/');
let state, busy=false, history=[], agentMode='agent', lastResult=null, events=[], toastTimer;
const welcomeHTML = $('#messages').innerHTML;
const emptyTraceHTML = $('#trace-body').innerHTML;
const names = {assistant:'Trợ lý AI',requests:'Đơn nghỉ phép',policies:'Chính sách nhân sự',presentation:'Góc trình bày'};

function toast(message) {$('#toast').textContent=message;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),4000);}
function navigate(page) {
  $$('.page').forEach(el=>el.classList.toggle('active',el.id===`page-${page}`));
  $$('.nav-item').forEach(el=>{el.classList.toggle('active',el.dataset.page===page);el.setAttribute('aria-current',el.dataset.page===page?'page':'false');});
  $('#breadcrumb').textContent=names[page];
  if(page==='requests') refreshState();
  if(page==='presentation') loadEvaluation();
}
function updateProviderLabel() {
  const offline=$('#provider-mode').value==='mock';
  $('#provider-label').textContent=offline?'Demo kịch bản · không dùng LLM':`${state?.llm.model || 'LLM'} · API thật`;
  $('#session-note').textContent=agentMode==='baseline'?'Chỉ phản hồi văn bản':'Có khả năng thực thi';
  $('#input-hint').textContent=offline?'Offline hỗ trợ câu mẫu · không dùng làm bằng chứng API thật':'Enter để gửi · Shift + Enter để xuống dòng';
}
function newChat() {
  if(busy) return toast('Đợi yêu cầu hiện tại hoàn tất trước khi mở cuộc trò chuyện mới.');
  history=[];lastResult=null;events=[];
  $('#messages').innerHTML=welcomeHTML;
  $('#trace-body').innerHTML=emptyTraceHTML;
  $('#message-input').value='';$('#trace-state').textContent='Sẵn sàng';$('#trace-state').className='trace-state';
  ['time','calls','tokens'].forEach(k=>$(`#trace-${k}`).textContent='—');
  $('#download-trace').disabled=true;fillIcons();updateProviderLabel();
}
function setBusy(value) {
  busy=value;
  $('#send-button').disabled=value;$('#provider-mode').disabled=value;
  $('#new-chat').disabled=value;$$('[data-agent-mode]').forEach(b=>b.disabled=value);
  $('#message-input').disabled=value;
}
async function refreshState(initial=false) {
  try {
    const res=await fetch('/api/state');if(!res.ok) throw Error('Không thể đọc workspace.');
    state=await res.json();
    const me=state.employees.find(e=>e.employee_id==='NV001');
    $('#available-days').textContent=me.available_days;
    const pending=state.requests.filter(r=>r.status==='PENDING').length;
    $('#pending-count').textContent=pending;$('#request-count').textContent=state.requests.length;
    $('#pending-caption').textContent=pending?'Chờ quản lý xét duyệt':'Chưa có yêu cầu đang chờ';
    $('#tool-count').textContent=state.tools.length;
    if(initial) {$('#provider-mode').value=state.llm.configured?'live':'mock';renderPolicies();renderPresentation();}
    updateProviderLabel();renderEmployees();renderRequests();
  } catch(err) {toast(err.message || 'Không thể kết nối máy chủ.');}
}
function renderEmployees() {
  $('#employee-grid').innerHTML=state.employees.map(e=>`<article class="employee-card"><div class="employee-head"><span class="avatar">${escapeHTML(e.full_name.split(' ').slice(-2).map(n=>n[0]).join(''))}</span><div><strong>${escapeHTML(e.full_name)}</strong><small>${e.employee_id} · ${escapeHTML(e.department)}</small></div></div><div class="employee-balance"><strong>${e.available_days}</strong><span>/ ${e.allowance} ngày phép khả dụng</span></div><div class="balance-bar"><span style="width:${e.available_days/e.allowance*100}%"></span><span class="pending" style="width:${e.pending_days/e.allowance*100}%"></span><span class="used" style="width:${e.used/e.allowance*100}%"></span></div><div class="balance-legend"><span>Khả dụng ${e.available_days}</span><span>Chờ duyệt ${e.pending_days}</span><span>Đã dùng ${e.used}</span></div><div class="employee-manager">Quản lý · ${escapeHTML(e.manager)}</div></article>`).join('');
}
function renderRequests() {
  if(!state) return;
  const filter=$('#employee-filter').value;
  const rows=state.requests.filter(r=>filter==='all'||r.employee_id===filter);
  if(!rows.length) {$('#request-table').innerHTML=`<div class="empty-table">${icon('calendar')}<h3>Chưa có đơn nghỉ phép</h3><p>Nhờ PeopleOps tạo đơn đầu tiên. Một khoảng nghỉ đang chờ bạn.</p></div>`;return;}
  $('#request-table').innerHTML=`<div class="table-scroll"><table><thead><tr><th>MÃ ĐƠN</th><th>NHÂN VIÊN & LÝ DO</th><th>THỜI GIAN NGHỈ</th><th>SỐ NGÀY</th><th>TRẠNG THÁI</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${escapeHTML(r.request_id)}</td><td>${escapeHTML(state.employees.find(e=>e.employee_id===r.employee_id)?.full_name || r.employee_id)}<small>${escapeHTML(r.reason)}</small></td><td>${dateVN(r.start_date)}<small>đến ${dateVN(r.end_date)}</small></td><td>${r.days} ngày</td><td><span class="badge pending">${r.status==='PENDING'?'Chờ duyệt':escapeHTML(r.status)}</span></td></tr>`).join('')}</tbody></table></div>`;
}
function renderPolicies() {
  const cards=[['annual_leave','sun','green','Ngày phép & quỹ phép'],['approval','calendar','amber','Quy trình xét duyệt'],['insurance','shield','blue','Bảo hiểm & quyền lợi'],['calendar','clock','mauve','Lịch làm việc demo']];
  $('#policy-grid').innerHTML=cards.map(([key,ico,color,title])=>`<article class="policy-card"><span class="stat-icon ${color}">${icon(ico)}</span><h2>${title}</h2><p>${escapeHTML(state.policies[key])}</p><small>PEOPLEOPS · SỔ TAY NHÂN SỰ DEMO V1.0</small></article>`).join('');
}
function renderPresentation() {
  const fits=[['Multi-step Reasoning',5,'Tra quỹ phép → tính ngày làm việc → kiểm tra điều kiện → tạo đơn.'],['Tool Interaction',5,'Cần dữ liệu SQLite và hành động tạo đơn qua MCP; text đơn thuần không đủ.'],['Dynamic Decision',5,'Đổi nhánh theo số dư, mã không tồn tại, trùng đơn hoặc thông tin còn thiếu.'],['Long Horizon Goal',2,'Mục tiêu ngắn trong một phiên, chưa có theo dõi dài hạn hay tự động nhắc quản lý.']];
  $('#fit-grid').innerHTML=fits.map(([name,score,desc])=>`<article class="fit-card"><div class="fit-score">${score}<span> / 5</span></div><h3>${name}</h3><p>${desc}</p><div class="fit-track"><span style="width:${score*20}%"></span></div></article>`).join('');
  const desc={hr_query:'Tra hồ sơ, số ngày phép và chính sách từ dữ liệu demo.',calculate_leave_days:'Tính ngày làm việc; loại cuối tuần và ngày đóng cửa demo.',create_leave_request:'Kiểm tra lại điều kiện, ghi đơn PENDING và giữ chỗ quỹ phép.',list_leave_requests:'Đọc danh sách đơn đã lưu cùng mã đơn và trạng thái.'};
  $('#tool-list').innerHTML=state.tools.map(t=>`<div class="tool-row"><code>${escapeHTML(t.name)}</code><p>${desc[t.name]}</p><span>${t.name==='create_leave_request'?'WRITE':'READ'}</span></div>`).join('');
}
async function loadEvaluation() {
  try {
    const res=await fetch('/api/evaluation');if(!res.ok) throw Error();const entries=await res.json();
    if(!entries.length){$('#evaluation-content').innerHTML='<div class="evaluation-content"><p>Chưa có kết quả nghiệm thu. Chạy python src/app.py --all để tạo bằng chứng API thật.</p></div>';return;}
    $('#evaluation-content').innerHTML=entries.map(e=>`<div class="evaluation-summary"><strong>${e.passed}/${e.total}</strong><p>${e.mode==='live'?'Nghiệm thu API thật':'Kiểm tra kịch bản offline'}<small>${new Date(e.generated_at).toLocaleString('vi-VN')} · Mỗi test dùng database riêng</small></p></div><div class="eval-items">${e.evaluations.map(t=>`<div class="eval-item ${t.passed?'':'fail'}"><strong>${t.id}</strong><span>${t.passed?'✓ PASS':'✕ FAIL'} · ${t.tool_calls} tools</span></div>`).join('')}</div>`).join('');
  } catch {$('#evaluation-content').textContent='Không tải được kết quả kiểm thử. Nhấn Làm mới để thử lại.';}
}
function addMessage(role,text,error=false) {
  $('#welcome')?.remove();
  const message=document.createElement('article');message.className=`message ${role} ${error?'error':''}`;
  if(role==='assistant'){const author=document.createElement('div');author.className='message-author';author.innerHTML=icon('sparkles')+'PeopleOps';message.append(author);}
  const bubble=document.createElement('div');bubble.className='bubble';
  if(role==='assistant')bubble.innerHTML=formatAnswer(text);else bubble.textContent=text;
  message.append(bubble);
  $('#messages').append(message);$('#messages').scrollTop=$('#messages').scrollHeight;
  return message;
}
function addTrace(e) {
  events.push(e);
  if(e.action_type==='RUN_START') return;
  if(e.action_type==='LLM_START'){$('#trace-state').textContent='Đang xử lý';return;}
  const definitions={MCP_READY:['Kết nối MCP','Đã tìm thấy 4 công cụ HR','ready'],THOUGHT:[`Vòng ${e.step} · Quyết định`,e.summary,'thought'],ACTION:['Action · '+e.tool_name,'Gọi công cụ qua MCP','action'],OBSERVATION:['Observation · '+e.observation?.status,e.tool_name,'observation'],FINAL_ANSWER:['Hoàn tất','Đã tổng hợp kết quả phản hồi','final'],ERROR:['Không hoàn tất',e.output,'error']};
  const [title,summary,cls]=definitions[e.action_type] || [e.action_type,'',''];
  const node=document.createElement('details');node.className=`trace-event ${cls}`;
  const heading=document.createElement('summary');
  const label=document.createElement('span');label.textContent=title;
  const time=document.createElement('span');time.className='trace-duration';time.textContent=e.latency_ms>0?`${e.latency_ms.toLocaleString('vi-VN')} ms`:'';
  heading.append(label,time);node.append(heading);
  const p=document.createElement('p');p.textContent=summary;node.append(p);
  const pre=document.createElement('pre');pre.textContent=JSON.stringify(e.arguments ?? e.observation ?? e.output ?? {summary:e.summary||summary,offset_ms:e.offset_ms},null,2);node.append(pre);
  if(e.latency_ms>0){const bar=document.createElement('div');bar.className='waterfall-bar';const part=document.createElement('span');part.style.width=`${Math.min(100,e.latency_ms/Math.max(e.offset_ms,1)*100)}%`;bar.append(part);node.append(bar);}
  $('#trace-body').append(node);$('#trace-body').scrollTop=$('#trace-body').scrollHeight;
  $('#trace-calls').textContent=events.filter(x=>x.action_type==='ACTION').length;
}
async function ask(text) {
  if(busy) return toast('PeopleOps đang xử lý yêu cầu hiện tại.');
  text=text.trim();if(!text) return;
  navigate('assistant');addMessage('user',text);$('#message-input').value='';
  setBusy(true);lastResult=null;events=[];$('#trace-body').replaceChildren();$('#download-trace').disabled=true;
  $('#trace-state').className='trace-state running';$('#trace-state').textContent='Đang kết nối';
  const typing=document.createElement('div');typing.className='typing';typing.setAttribute('aria-label','PeopleOps đang xử lý');typing.innerHTML='<i></i><i></i><i></i>';$('#messages').append(typing);$('#messages').scrollTop=$('#messages').scrollHeight;
  const start=performance.now();const timer=setInterval(()=>$('#trace-time').textContent=((performance.now()-start)/1000).toFixed(1)+' s',100);
  $('#trace-calls').textContent='0';$('#trace-tokens').textContent='—';
  let finished=false;
  try {
    const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,mode:$('#provider-mode').value,baseline:agentMode==='baseline',history})});
    if(!response.ok){const err=await response.json();throw Error(typeof err.detail==='string'?err.detail:'Yêu cầu không hợp lệ. Vui lòng kiểm tra nội dung.');}
    const reader=response.body.getReader(), decoder=new TextDecoder();let buffer='';
    const processLine=line=>{
      if(!line.trim())return;
      const data=JSON.parse(line);
      if(data.type==='event')addTrace(data.event);
      if(data.type==='error')throw Error(data.message);
      if(data.type==='done'){
        finished=true;lastResult=data.result;typing.remove();
        const message=addMessage('assistant',lastResult.answer,lastResult.status==='error');
        const meta=document.createElement('div');meta.className='message-meta';meta.textContent=`${lastResult.live?lastResult.model:'Demo offline'} · ${lastResult.tool_calls} tool calls · ${(lastResult.duration_ms/1000).toFixed(1)}s`;message.append(meta);
        $('#trace-state').textContent=lastResult.status==='error'?'Có lỗi':'Hoàn tất';$('#trace-state').className='trace-state '+(lastResult.status==='error'?'error':'');
        $('#trace-tokens').textContent=lastResult.tokens.toLocaleString('vi-VN');$('#download-trace').disabled=false;
        if(lastResult.status==='completed'){history.push({role:'user',content:text},{role:'assistant',content:lastResult.answer});history=history.slice(-12);}
      }
    };
    while(true){const {value,done}=await reader.read();if(done){buffer+=decoder.decode();if(buffer.trim())processLine(buffer);break;}buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();lines.forEach(processLine);}
    if(!finished)throw Error('Kết nối bị ngắt trước khi hoàn tất. Kiểm tra danh sách đơn trước khi gửi lại.');
  } catch(err){typing.remove();addMessage('assistant',err instanceof TypeError?'Mất kết nối máy chủ. Vui lòng kiểm tra mạng và danh sách đơn trước khi gửi lại.':err.message||'Không thể kết nối máy chủ.',true);$('#trace-state').textContent='Có lỗi';$('#trace-state').className='trace-state error';}
  finally {clearInterval(timer);typing.remove();$('#trace-time').textContent=((lastResult?.duration_ms ?? performance.now()-start)/1000).toFixed(1)+' s';setBusy(false);await refreshState();$('#message-input').focus();}
}
function openLeaveDialog(){if(busy)return toast('Đợi yêu cầu hiện tại hoàn tất nhé.');$('#leave-dialog').showModal();}
fillIcons();
$$('[data-page]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.page)));
$$('[data-agent-mode]').forEach(b=>b.addEventListener('click',()=>{if(busy)return;agentMode=b.dataset.agentMode;$$('[data-agent-mode]').forEach(x=>x.classList.toggle('selected',x===b));newChat();}));
$('#provider-mode').addEventListener('change',newChat);
$('#new-chat').addEventListener('click',()=>{newChat();toast('Đã mở cuộc trò chuyện mới. Các đơn đã lưu vẫn được giữ.');});
$('#chat-form').addEventListener('submit',e=>{e.preventDefault();ask($('#message-input').value);});
$('#message-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();ask(e.target.value);}});
$('#messages').addEventListener('click',e=>{const btn=e.target.closest('[data-prompt]');if(!btn)return;const kind=btn.dataset.prompt;if(kind==='create')return openLeaveDialog();const prompts={balance:'Hãy tra cứu quỹ phép còn lại của NV001.',policy:'Tra cứu chính sách bảo hiểm và nghỉ phép áp dụng cho NV001 trong dữ liệu demo.',insufficient:'Nếu đủ phép, tạo đơn cho NV003 từ 21/09/2026 đến 25/09/2026, lý do: du lịch.'};ask(prompts[kind]);});
['#hero-create','#requests-create'].forEach(s=>$(s).addEventListener('click',openLeaveDialog));
$('#close-dialog').addEventListener('click',()=>$('#leave-dialog').close());
$('#leave-dialog').addEventListener('click',e=>{if(e.target===e.currentTarget){const r=e.currentTarget.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.currentTarget.close();}});
$('#leave-form').addEventListener('submit',e=>{e.preventDefault();const start=$('#leave-start').value,end=$('#leave-end').value,reason=$('#leave-reason').value.trim();if(start>end)return toast('Ngày kết thúc phải từ ngày bắt đầu trở đi.');if(reason.length<3)return toast('Nhập lý do nghỉ có ít nhất 3 ký tự.');$('#leave-dialog').close();if(agentMode==='baseline'){agentMode='agent';$$('[data-agent-mode]').forEach(x=>x.classList.toggle('selected',x.dataset.agentMode==='agent'));newChat();}ask(`Tạo đơn nghỉ phép cho ${$('#leave-employee').value} từ ${dateVN(start)} đến ${dateVN(end)}, lý do: ${reason}.`);});
$('#employee-filter').addEventListener('change',renderRequests);
$('#refresh-evaluation').addEventListener('click',loadEvaluation);
$('#print-presentation').addEventListener('click',()=>window.print());
$('#download-trace').addEventListener('click',()=>{if(!lastResult)return;const url=URL.createObjectURL(new Blob([JSON.stringify(lastResult,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`peopleops-trace-${lastResult.run_id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
refreshState(true);
