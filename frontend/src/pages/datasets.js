import{datasets}from'../stores/dataset.js';
import{create,addSegment,seal}from'../api/dataset.js';
import{header}from'../components/common/header.js';
import{table}from'../components/common/table.js';
import{esc,json}from'../utils/html.js';
import{submit,notify}from'../hooks/feedback.js';
import{session}from'../stores/session.js';
import{BATCH_STATUSES}from'../constants/enums.js';

const gapText=gaps=>gaps.length?gaps.map(([a,b])=>a===b?String(a):a+'–'+b).join('、'):'无缺口';

export async function datasetsPage(el){
  const rows=await datasets.load();
  const writable=session.get().role!=='viewer';
  el.innerHTML=header('01','每一次覆盖，都保留写入顺序','断网后按段补传：每段声明起始序号，允许乱序、重叠与重试；只有连续序号补齐并封存后，批次才可发起试验。')+`<p class="modelnote">教学存储模型：Python 实现 memtable / SSTable / compaction；MySQL 仅持久化业务输入、结果与分段收据，不代表真实 MySQL 存储引擎。</p><div class="split"><section class="panel"><span class="material-tag">WRITE SPECIMENS / ${rows.length}</span>${rows.map(x=>`<article class="record"><h3>${esc(x.name)} <span class="badge ${x.status==='sealed'?'passed':''}">${esc(BATCH_STATUSES[x.status]||x.status)}</span></h3><p class="muted">${esc(x.description)}</p><span class="badge">${x.operation_count} OPS / ${x.distinct_keys} KEYS</span>${x.status==='receiving'?`<span class="badge">已收 ${x.received_count} / 声明 ${x.total_count}</span><span class="badge ${x.gaps.length?'failed':''}">缺口 ${esc(gapText(x.gaps))}</span>`:''}${x.segments?.length?`<details open><summary>分段收据 · ${x.segments.length} 段</summary>${table(['起始序号','条数','内容摘要'],x.segments.map(s=>[s.start_seq,s.count,'<span class="mono">'+esc(s.content_hash.slice(0,12))+'</span>']))}</details>`:''}${x.entries.length?`<pre>${json(x.entries.slice(0,4))}${x.entries.length>4?'\n…':''}</pre><details><summary>查看封存操作序列</summary><pre>${json(x.entries)}</pre></details>`:'<p class="muted">尚未封存：已收分段按起始序号暂存，封存时按原序号拼接。</p>'}<div class="actions">${x.status==='sealed'?`<a href="#trials/${x.id}">以此批次发起试验 →</a>`:x.gaps.length?`<span class="muted">补齐序号 ${esc(gapText(x.gaps))} 后才能封存</span>`:`<button class="primary" data-seal data-dataset="${x.id}">连续序号已补齐 · 封存为可试验</button>`}</div></article>`).join('')}</section><aside class="panel"><h2>${writable?'登记与补传':'输入契约'}</h2>${writable?`<form id="dataset-form"><label>批次名称</label><input name="name" required maxlength="120" placeholder="north-edge-20261117"><label>业务说明</label><input name="description" required maxlength="2000" placeholder="说明站点、重复键和删除策略"><label>声明总条数 · 直接完整登记时留空</label><input type="number" name="total_count" min="1" max="2000" placeholder="12"><label>完整登记 · JSON 数组（留空则先建接收中批次）</label><textarea name="entries" rows="8">[
  {"op":"put","key":"sensor-01","value":"18.2"},
  {"op":"put","key":"sensor-02","value":"19.1"},
  {"op":"delete","key":"sensor-01"}
]</textarea><div class="actions"><button type="submit" class="primary">保存写入批次</button></div></form><form id="segment-form" style="margin-top:30px;border-top:1px solid var(--line);padding-top:10px"><h2>断网续传一段</h2><label>接收中批次</label><select name="dataset_id">${rows.filter(x=>x.status==='receiving'&&x.total_count).map(x=>`<option value="${x.id}">#${x.id} ${esc(x.name)} · 已收 ${x.received_count}/${x.total_count}</option>`).join('')||'<option value="">暂无接收中批次</option>'}</select><label>起始序号 · 从 1 开始</label><input type="number" name="start_seq" min="1" max="2000" required><label>本段有序操作 · JSON 数组</label><textarea name="operations" rows="6">[
  {"op":"put","key":"sensor-03","value":"22.4"}
]</textarea><div class="actions"><button type="submit">补传这一段</button></div></form>`:''}<p class="helper">1–2000 条操作；键1–64字，值为不超过200字的字符串。重传相同序号相同内容不重复写入；内容冲突整段拒绝且保留已收分段。封存后禁止追加，也不可再补传。</p></aside></div>`;
  if(!writable)return;
  el.querySelector('#dataset-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{
    const d=Object.fromEntries(new FormData(e.target));
    d.total_count=d.total_count?Number(d.total_count):null;
    if(!d.entries.trim())d.entries=[];else{try{d.entries=JSON.parse(d.entries)}catch{throw Error('操作JSON格式错误，请检查引号与逗号')}}
    if(!d.entries.length&&!d.total_count)throw Error('请声明总条数，或直接提供完整操作序列');
    await create(d);notify(d.entries.length?'写入批次已登记并封存':'接收中批次已建立，请逐段补传');await datasetsPage(el)
  })};
  const sf=el.querySelector('#segment-form');
  sf.onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{
    const d=Object.fromEntries(new FormData(e.target));
    if(!d.dataset_id)throw Error('没有可补传的接收中批次');
    d.start_seq=Number(d.start_seq);
    try{d.operations=JSON.parse(d.operations)}catch{throw Error('操作JSON格式错误，请检查引号与逗号')}
    if(!Array.isArray(d.operations)||!d.operations.length)throw Error('本段至少包含1条操作');
    d.count=d.operations.length;
    const r=await addSegment(Number(d.dataset_id),{start_seq:d.start_seq,count:d.count,operations:d.operations});
    notify(r.replayed?'该段已收过，内容一致，本次未重复写入':`已收序号 ${r.segments.map(s=>s.start_seq+'-'+(s.start_seq+s.count-1)).join('、')}，缺口 ${gapText(r.gaps)}`);
    await datasetsPage(el)
  })};
  el.querySelectorAll('[data-seal]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{const r=await seal(Number(b.dataset.dataset));notify(r.already_sealed?'批次已封存，无需重复封存':'批次已封存，可发起试验');await datasetsPage(el)}catch(e){notify(e.message);b.disabled=false}});
}
