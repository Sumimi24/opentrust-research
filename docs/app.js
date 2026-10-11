const $=id=>document.getElementById(id);
const pct=x=>x==null?'不可估计':(100*x).toFixed(1)+'%';
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const short={'gpt-5.4':'GPT','qwen3.8-max':'Qwen','deepseek-v4-pro':'DeepSeek','kimi-k2.5':'Kimi'};
const routeNames={'fixed_gpt-5.4':'固定 GPT','fixed_qwen3.8-max':'固定 Qwen','fixed_deepseek-v4-pro':'固定 DeepSeek','global_calibration':'校准集选全局审核','producer_calibration':'按生产者选择审核','random_hash':'随机路线','blind_global_agreement':'盲解答案一致','all_three_agree':'三审核一致','shuffled_producer_route':'打乱生产者身份'};
const families={transaction:'事务提交',lease:'资源与租约',request:'请求与确认'};
const colors=['#067f77','#aa6d2d','#587da0','#37665e','#b4533e','#879748','#7063a1','#112f47','#a57587'];
let DATA;

function renderResults(){
 const d=DATA.protocol,c=d.completion;
 $('study-status').textContent=`已完成并核对：${c.independent_specs} 个生成场景，${DATA.scope.unique_parameter_configurations} 种参数配置；${c.actual_calls.toLocaleString()} 次正式文本调用。接口失败按冻结规则保留。`;
 $('headline-stats').innerHTML=[[c.independent_specs,'文本生成场景（51 种参数配置）'],c.candidates? [c.candidates,'自然产生的分析答案']:[0,'分析答案'],[c.reviews,'全交叉审核结果'],[DATA.rtl.summary?.initial_cases||'待完成','开源 RTL 初始修复例']].map(([n,t])=>`<div><b>${n.toLocaleString()}</b><span>${t}</span></div>`).join('');
 $('protocol-meta').innerHTML=['120 场景 · 51 参数配置 · 240 轨迹','30 校准场景 / 90 测试场景','4 个分析模型 · 3 个审核模型','另有 720 次盲解对照','参数可重复，全部轨迹不同','每条分析单次调用 · 无静默重试'].map(x=>`<span>${x}</span>`).join('');
 $('calls-meta').textContent=`正式调用 ${d.calls.actual.toLocaleString()} 次：完整返回 ${d.calls.statuses.complete} 次，网络失败 ${d.calls.statuses.transport_error||0} 次。API 报告 ${d.calls.usage.total_tokens.toLocaleString()} tokens；另有两轮 pilot 共 456 次调用，单独保留。全交叉采集费用与单条部署路线费用分开，未核验单价时不报告金额。`;
 $('producer-bars').innerHTML=Object.entries(d.producers).map(([m,r])=>`<div class="bar-row"><span>${esc(short[m])}</span><div class="bar-track"><div class="bar-fill" style="width:${100*r.correct/r.n}%"></div></div><span>${r.correct}/${r.n} · ${pct(r.correct/r.n)}</span></div>`).join('');
 let html='<caption>独立测试集配对漏检率 φ，分母为该生产者的错误答案</caption><thead><tr><th>生产者 ↓ / 审核者 →</th>'+DATA.reviewers.map(m=>`<th>${esc(short[m])}</th>`).join('')+'</tr></thead><tbody>';
 for(const producer of DATA.producers){html+=`<tr><th>${esc(short[producer])}</th>`;for(const reviewer of DATA.reviewers){const r=d.matrix.find(x=>x.producer===producer&&x.reviewer===reviewer);const v=r.false_endorsement;html+=`<td class="matrix-cell" style="background:rgba(173,79,49,${v==null?0:.04+v*.25})"><b>${pct(v)}</b><small>${r.false_accepted}/${r.bad} · 放行 ${r.accepted}/${r.n}</small></td>`;}html+='</tr>';}
 $('pair-matrix').innerHTML=html+'</tbody>';
 $('protocol-conclusion').textContent=DATA.protocol_conclusion;
 $('abstract-text').textContent=DATA.abstract;
 $('composition-history').textContent=DATA.history;
 $('artifact-audit').textContent=DATA.audit_caption;
 renderRoutes();renderEngineering();setupDemo();
}

function renderRoutes(){
 const family=$('family-filter').value;const routes=family==='all'?DATA.protocol.routes:DATA.protocol.families[family];
 $('route-table').innerHTML='<caption>'+ (family==='all'?'总体独立测试；同一规格下答案相关':'协议族：'+families[family])+'</caption><thead><tr><th>路线</th><th>正确放行 / 全部</th><th>错误放行 / 放行</th><th>漏检 φ</th><th>覆盖率</th><th>放行后错误率</th><th>审核次数</th></tr></thead><tbody>'+Object.entries(routes).map(([name,r])=>`<tr><th>${esc(routeNames[name])}</th><td>${r.correct_accepted}/${r.n}</td><td>${r.false_accepted}/${r.accepted}</td><td>${pct(r.false_endorsement)}</td><td>${pct(r.coverage)}</td><td>${pct(r.conditional_risk)}</td><td>${name==='all_three_agree'?3:1}</td></tr>`).join('')+'</tbody>';
 const a=routes.producer_calibration,b=routes.global_calibration;
 const diff=DATA.protocol.paired_difference_producer_minus_global;
 $('route-reading').innerHTML=`<p><strong>全局审核</strong>由校准集选择 ${esc(short[DATA.protocol.calibration_selection.global_reviewer])}。${esc(Object.entries(DATA.protocol.calibration_selection.producer_reviewers).map(([p,v])=>short[p]+' → '+short[v]).join('；'))}。</p><p>按生产者路线：放行 ${a.accepted}/${a.n}，其中错误 ${a.false_accepted}；全局路线：放行 ${b.accepted}/${b.n}，其中错误 ${b.false_accepted}。</p>`+(family==='all'?`<p>按生产者减去全局的风险差，规格分簇重采样 95% 描述区间：${diff.conditional_risk?diff.conditional_risk.map(x=>(100*x).toFixed(1)).join(' 至 ')+' 个百分点':'不可估计'}。区间跨零时不能据此宣称稳定优势。</p>`:'<p>分族表显示频数；总体区间不能直接当作本协议族的区间。</p>');
 let svg='<rect width="560" height="350" fill="white"/>';
 const keys=Object.keys(routes),valid=keys.map(k=>routes[k].conditional_risk).filter(x=>x!=null);const ymax=Math.max(.1,...valid)*1.15;
 for(let j=0;j<=4;j++){let y=280-j*55;svg+=`<line x1="65" y1="${y}" x2="520" y2="${y}" stroke="#e0e9e4"/><text x="53" y="${y+4}" text-anchor="end" font-size="10" fill="#566976">${pct(ymax*j/4)}</text>`;let x=65+j*113.75;svg+=`<text x="${x}" y="300" text-anchor="middle" font-size="10" fill="#566976">${j*25}%</text>`;}
 svg+='<line x1="65" y1="60" x2="65" y2="280" stroke="#566976"/><line x1="65" y1="280" x2="520" y2="280" stroke="#566976"/><text x="300" y="325" text-anchor="middle" font-size="12" fill="#172f3b">放行覆盖率 →</text><text x="10" y="35" font-size="12" fill="#172f3b">放行后的错误率</text>';
 keys.forEach((k,i)=>{const r=routes[k];if(r.conditional_risk==null)return;const x=65+455*r.coverage,y=280-220*r.conditional_risk/ymax;svg+=`<circle cx="${x}" cy="${y}" r="5" fill="${colors[i]}"><title>${esc(routeNames[k])}：覆盖 ${pct(r.coverage)}，风险 ${pct(r.conditional_risk)}</title></circle>`;});
 keys.forEach((k,i)=>{let x=80+(i%3)*153,y=12+Math.floor(i/3)*14;svg+=`<rect x="${x}" y="${y}" width="7" height="7" fill="${colors[i]}"/><text x="${x+12}" y="${y+7}" font-size="8" fill="#172f3b">${esc(routeNames[k])}</text>`;});
 $('risk-chart').innerHTML=svg;
}

function renderEngineering(){
 const r=DATA.rtl;
 if(!r.summary?.complete){$('rtl-new-results').innerHTML='<div class="note">新一轮开源骨架修复正在运行；暂不展示未完成的通过率。前一轮已完成结果保留在下方。</div>';const link=document.querySelector('a[href="assets/rtl-repair-study.zip"],a[data-pending-href="assets/rtl-repair-study.zip"]');link.removeAttribute('href');link.setAttribute('aria-disabled','true');link.querySelector('span').textContent='完整实验包将在修复与独立测试完成、审计通过后提供。';return;}
 const names={direct_patch:'单次修复',same_family_trace:'同家族继续修复',cross_family_trace:'跨家族继续修复'};
 $('rtl-new-results').innerHTML=`<h3 class="subheading">新一轮：18 个已验证缺陷 × 4 个模型</h3><p>${r.summary.initial_cases} 份初始修复，${r.summary.route_rows} 条配对路线。每条路线最多三次模型调用，开发通过即停止。相同初始答案和开发反例共享，独立测试前冻结源码。</p><div class="table-scroll"><table><caption>新一轮独立测试结果；三个独立种子须全部通过</caption><thead><tr><th>路线</th><th>独立通过</th><th>正确采纳</th><th>错误采纳</th><th>逻辑调用</th></tr></thead><tbody>${Object.entries(r.summary.methods).map(([m,x])=>`<tr><th>${names[m]}</th><td>${x.independent_pass}/${x.n}</td><td>${x.correct_adoption}/${x.n}</td><td>${x.false_adoption}</td><td>${x.logical_calls}</td></tr>`).join('')}</tbody></table></div><p class="small">实际 API 调用 ${r.summary.actual_calls} 次，初始修复在两条继续路线共享；逻辑调用不能相加当成实际费用。固定 GPT 三次调用对照包含在 GPT 初始的同家族路线中。</p>`;
}

function setupDemo(){
 $('case-picker').innerHTML=DATA.examples.map(c=>`<option value="${esc(c.id)}">${families[c.family]} · ${esc(c.id)} · ${c.events.length} 事件</option>`).join('');
 $('producer-picker').innerHTML=DATA.producers.map(m=>`<option value="${esc(m)}">${short[m]}</option>`).join('');
 $('reviewer-picker').innerHTML=DATA.reviewers.map(m=>`<option value="${esc(m)}">${short[m]}</option>`).join('');
 $('case-picker').addEventListener('change',()=>{const c=DATA.examples.find(x=>x.id===$('case-picker').value);$('event-slider').value=Math.min(c.events.length,c.truth.first_bad_event||10);renderCase();});
 for(const id of ['producer-picker','reviewer-picker','event-slider'])$(id).addEventListener('input',renderCase);
 $('previous-event').addEventListener('click',()=>{$('event-slider').value=Math.max(1,Number($('event-slider').value)-1);renderCase();});
 $('next-event').addEventListener('click',()=>{$('event-slider').value=Math.min(Number($('event-slider').max),Number($('event-slider').value)+1);renderCase();});
 const first=DATA.examples[0];$('event-slider').max=first.events.length;$('event-slider').value=Math.min(first.events.length,first.truth.first_bad_event||10);renderCase();
}

function renderCase(){
 const c=DATA.examples.find(x=>x.id===$('case-picker').value),p=$('producer-picker').value,v=$('reviewer-picker').value;
 const proposal=c.answers.find(x=>x.producer===p),review=c.reviews.find(x=>x.producer===p&&x.reviewer===v);
 $('case-title').textContent=families[c.family];$('case-spec').textContent='参数：'+JSON.stringify(c.spec);
 $('event-slider').max=c.events.length;const n=Number($('event-slider').value);$('event-count').textContent=n+' / '+c.events.length;
 $('trace-events').innerHTML=c.events.slice(Math.max(0,n-10),n).map((e,i)=>{const j=Math.max(0,n-10)+i+1;return `<span${j===c.truth.first_bad_event?' class="bad-event"':''}>${j}: ${esc(JSON.stringify(e))}</span>`;}).join('\n');
 $('case-truth').textContent=JSON.stringify(c.truth,null,2);$('case-proposal').textContent=proposal.raw_text||'(没有完整返回)';
 $('case-accuracy').className=proposal.correct?'good':'bad';$('case-accuracy').textContent=proposal.correct?'分析与真值一致':'分析与真值不一致';
 const danger=review.accepted&&!proposal.correct;const text=review.accepted?(proposal.correct?'放行：正确采纳':'放行：错误采纳'):(proposal.correct?'拒绝：误拒正确答案':'拒绝：拦截错误答案');
 $('case-review').className=danger?'bad':'good';$('case-review').textContent=text+(review.parse_valid?'':'（审核接口或格式失败，按规则拒绝）');
}

$('family-filter').addEventListener('change',renderRoutes);
fetch('assets/data.json').then(r=>{if(!r.ok)throw Error('data unavailable');return r.json();}).then(d=>{DATA=d;renderResults();}).catch(error=>{console.error(error);$('study-status').textContent='实验数据尚未就绪或暂时无法加载。请从 GitHub 仓库检查已完成的审计材料。';});
