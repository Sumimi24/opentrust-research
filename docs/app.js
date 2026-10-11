const $=id=>document.getElementById(id);
const pct=x=>x==null?'不可估计':(100*x).toFixed(1)+'%';
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const short={'gpt-5.4':'GPT','qwen3.8-max':'Qwen','deepseek-v4-pro':'DeepSeek','kimi-k2.5':'Kimi'};
const routeNames={'fixed_gpt-5.4':'固定 GPT','fixed_qwen3.8-max':'固定 Qwen','fixed_deepseek-v4-pro':'固定 DeepSeek','global_calibration':'校准集选全局审核','producer_calibration':'按生产者选择审核','random_hash':'随机路线','blind_global_agreement':'盲解答案一致','all_three_agree':'三审核一致','shuffled_producer_route':'打乱生产者身份'};
const families={transaction:'事务提交',lease:'资源与租约',request:'请求与确认'};
const caseRules={transaction:'合同要点：PREPARE(id,p)只禁止该事务再次向参与者p写入，其他尚未准备的参与者仍可WRITE；COMMIT要求所有参与者已准备。事务ID不复用，轨迹结束时所有事务须关闭。',lease:'合同要点：租约在t≥expiry时自动过期，到期时刻不可USE或RENEW；过期或释放后ID可以复用。所有未过期租约的资源总量不能超容量，结束时不能仍有活动租约。',request:'合同要点：DATA序号从0连续增加，每块及累计字节受限；累计恰好等于提交长度才可COMPLETE。t>deadline时先判超时，t=deadline允许处理；请求ID不复用，结束时所有请求须关闭。'};
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
 $('route-reading').innerHTML=`<p><strong>全局审核</strong>由校准集选择 ${esc(short[DATA.protocol.calibration_selection.global_reviewer])}。${esc(Object.entries(DATA.protocol.calibration_selection.producer_reviewers).map(([p,v])=>short[p]+' → '+short[v]).join('；'))}。</p><p>按生产者路线：放行 ${a.accepted}/${a.n}，其中错误 ${a.false_accepted}；全局路线：放行 ${b.accepted}/${b.n}，其中错误 ${b.false_accepted}。</p>`+(family==='all'?`<p>按生产者减去全局的风险差，生成场景分簇重采样 95% 描述区间：${diff.conditional_risk?diff.conditional_risk.map(x=>(100*x).toFixed(1)).join(' 至 ')+' 个百分点':'不可估计'}。区间跨零时不能据此宣称稳定优势。</p>`:'<p>分族表显示频数；总体区间不能直接当作本协议族的区间。</p>');
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
 if(!r.precision?.complete||!r.smoke?.summary?.complete){
  $('rtl-new-results').innerHTML='<div class="note">工程模型调用已结束；执行复评与前置门控 smoke 尚在进行。完整结果在独立测试与审计结束后展示。</div>';
  const link=document.querySelector('a[href="assets/rtl-repair-study.zip"],a[data-pending-href="assets/rtl-repair-study.zip"]');link.removeAttribute('href');link.setAttribute('aria-disabled','true');link.querySelector('span').textContent='工程实验包将在执行复评、门控 smoke 与审计通过后提供。';return;
 }
 const names={direct_patch:'单次修复',same_family_trace:'同家族继续修复',cross_family_trace:'跨家族继续修复'};
 const tasks={dma_write:'DMA 写通路',udp_rx_guard:'UDP 接收链路',icache_ctrl:'取指缓存'};
 const a=r.precision_audit,ci=a.cross_minus_same_correct_adoption_difference95;
 const table=(caption,heads,rows)=>`<div class="table-scroll"><table><caption>${caption}</caption><thead><tr>${heads.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(c=>`<tr><th>${c[0]}</th>${c.slice(1).map(v=>`<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
 let html=`<h3 class="subheading">18 个已验证缺陷 × 4 个初始模型</h3><p>72 份初始修复，216 条共享起点的路线。继续路线最多三次总调用，原开发放行后停止并冻结源码。下方采用修正执行环境后的独立评分，结合原指令的源码必要条件，评价原采纳决定；不把开发拒绝者倒算为成功采纳。</p><figure><img class="export-figure" src="assets/figures/rtl-correct-adoption.svg" alt="DMA、UDP和取指缓存的三种路线经执行复评后的正确采纳数量"/><figcaption class="small">原决定 + 源码必要条件 + 校正后的三个独立种子。属于本批固定合同与注入缺陷的证据。</figcaption></figure>`;
 html+=table('冻结原决定，校正执行评分；每条路线 n = 72',['路线','校正功能独立通过','合同正确采纳','合同错误采纳','逻辑调用'],Object.entries(r.precision.methods).map(([m,x])=>[names[m],`${x.regraded_independent_pass}/${x.n}`,`${x.frozen_correct_adoption}/${x.n}`,x.frozen_false_adoption,r.summary.methods[m].logical_calls]));
 html+='<p class="small">“功能独立通过”只描述测试结果；合同正确采纳还须原开发放行并满足源码必要条件。存在核心实例仅是必要检查，不证明每个输出都依赖核心，也不构成形式化硬件正确性证明。</p>';
 html+=table('按任务的合同正确采纳；每格 6 个注入缺陷 × 4 个模型',['任务',...Object.values(names)],Object.entries(a.tasks).map(([t,methods])=>[tasks[t],...Object.keys(names).map(m=>`${methods[m].correct_adoption}/${methods[m].n}`)]));
 html+=`<p>跨家族减去同家族正确采纳率，按任务分层、18 个缺陷分簇的 95% 描述性重采样区间为 ${ci.map(x=>(100*x).toFixed(1)).join(' 至 ')} 个百分点。区间只描述本缺陷集合，不能代表真实历史缺陷或新工程项目。执行问题曾进入开发反馈，复评不能撤销这些影响；方法比较保留该限制。</p>`;
 html+=table('固定 GPT 配对对照：相同 GPT 初始修复，每条路线 n = 18',['路线','合同正确采纳','合同错误采纳','逻辑调用'],Object.entries(a.GPT_initial_paired_routes).map(([m,x])=>[names[m],`${x.correct_adoption}/${x.n}`,x.false_adoption,x.logical_calls]));
 html+=`<p class="small">原批实际 API 调用 ${r.summary.actual_calls} 次，API 报告 ${r.audit.usage_tokens.total_tokens.toLocaleString()} tokens。初始修复在继续路线共享，逻辑调用不能相加当成实际费用。相同三次上限不代表相同实际调用数或 token 成本；单次路线为低预算起点。</p>`;
 html+='<h3 class="subheading">评分执行问题怎样修正</h3><p>原独立阶段重新上传相同源码，刷新文件时间，触发 Verilator 在 OSS 上覆盖生成文件失败。修正版按内容哈希核验、保留源码，并在新的评分目录重新编译；同时提供默认 1 ns / 1 ps。全部最终源码、功能断言、原采纳决定保持不变，参考与 18 个缺陷重新资格检查，无新增模型调用。</p>';
 html+=table('原执行诊断保留；这些执行失败不能直接判为模型功能错误',['路线','原开发放行','原独立评分通过','含文件系统失败'],Object.entries(r.summary.methods).map(([m,x])=>[names[m],x.correct_adoption+x.false_adoption,`${x.independent_pass}/${x.n}`,r.audit.independent_result_categories[m].environment_filesystem||0]));
 html+=`<p>最终开发评分的 ${r.audit.final_development_time_precision_rows.length} 条时间精度失败路线中，保留核心实例的为 ${r.audit.final_development_time_precision_rows.filter(x=>x.core_instance_present).length} 条。缺少核心的重实现已违反原集成指令；补齐时间环境不会让这些源码获得采纳资格。逐项原始记录、修正执行及源码复核均在实验包。</p>`;
 html+=table('原开发拒绝、校正后独立通过：仅作诊断',['路线','原拒绝但复评通过'],Object.entries(r.precision.methods).map(([m,x])=>[names[m],x.development_rejected_but_independent_pass]));
 const smoke=r.smoke.summary,sa=r.smoke.audit,sx=smoke.methods.cross_family_trace;
 html+='<h3 class="subheading">修正后的工程线路：12 例流程 smoke</h3><p>把开源核心与唯一包装模块检查放到执行前，保留原始集成代码作为每轮修复上下文，并使用固定时间精度与不可变源码上传。三任务各 4 个初始模型，每例含初始生成最多三次总调用，开发／独立种子均为新种子。此轮用于检查流水线，不估计相对旧实验的改进幅度。</p>';
 html+=table('新的门控流水线 smoke',['任务','正确采纳','错误采纳'],Object.entries(sa.tasks).map(([t,x])=>[tasks[t],`${x.correct_adoption}/${x.n}`,x.false_adoption]));
 html+=`<p>合计正确采纳 ${sx.correct_adoption}/12，错误采纳 ${sx.false_adoption}；实际调用 ${smoke.actual_calls} 次。参考资格 ${sa.reference_seed_passes}/15，三个选定功能缺陷均检出，三个遗漏核心控制例在仿真前拒绝。源码先冻结，再独立测试；完整独立种子 ${sa.new_independent_seeds.join('、')}。</p>`;
 const categories={pass:'独立通过',functional_assertion:'功能断言失败',compile_or_runtime_error:'编译或运行失败',missing_module:'缺少指定模块',extra_module:'额外模块',missing_upstream_core:'遗漏开源核心',forbidden_test_control:'禁止的测试控制',simulation_system_task:'仿真系统任务',preprocessor_access:'禁止的预处理访问'};
 html+=`<p class="small">最终独立评分类别：${Object.entries(sa.independent_result_categories).map(([k,v])=>esc(categories[k]||k)+' '+v+' 例').join('；')}。本批未检出已知文件系统覆盖失败；这不等于证明不存在其他执行缺陷。</p>`;
 $('rtl-new-results').innerHTML=html;
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
 $('case-rule').textContent=caseRules[c.family];
 $('event-slider').max=c.events.length;const n=Number($('event-slider').value);$('event-count').textContent=n+' / '+c.events.length;
 $('trace-events').innerHTML=c.events.slice(Math.max(0,n-10),n).map((e,i)=>{const j=Math.max(0,n-10)+i+1;return `<span${j===c.truth.first_bad_event?' class="bad-event"':''}>${j}: ${esc(JSON.stringify(e))}</span>`;}).join('\n');
 $('case-truth').textContent=JSON.stringify(c.truth,null,2);$('case-proposal').textContent=proposal.raw_text||'(没有完整返回)';
 $('case-accuracy').className=proposal.correct?'good':'bad';$('case-accuracy').textContent=proposal.correct?'分析与真值一致':'分析与真值不一致';
 const danger=review.accepted&&!proposal.correct;const text=review.accepted?(proposal.correct?'放行：正确采纳':'放行：错误采纳'):(proposal.correct?'拒绝：误拒正确答案':'拒绝：拦截错误答案');
 $('case-review').className=danger?'bad':'good';$('case-review').textContent=text+(review.parse_valid?'':'（审核接口或格式失败，按规则拒绝）');
 const blind=c.blind_answers.find(x=>x.reviewer===v);
 const matched=Boolean(proposal.answer&&blind.answer&&['valid','first_bad_event','rule'].every(k=>proposal.answer[k]===blind.answer[k]));
 $('case-blind').textContent=blind.raw_text||'(没有完整且可解析的盲解)';
 $('case-blind-accuracy').className=blind.correct?'good':'bad';$('case-blind-accuracy').textContent=blind.correct?'盲解本身与CPU真值一致':'盲解本身也与CPU真值不一致';
 $('case-blind-decision').className=matched&&!proposal.correct?'bad':'good';
 $('case-blind-decision').textContent=matched?(proposal.correct?'盲解一致：正确采纳':'盲解一致：仍然错误采纳'):'盲解不一致或格式失败：拒绝提案';
}

$('family-filter').addEventListener('change',renderRoutes);
fetch('assets/data.json').then(r=>{if(!r.ok)throw Error('data unavailable');return r.json();}).then(d=>{DATA=d;renderResults();}).catch(error=>{console.error(error);$('study-status').textContent='实验数据尚未就绪或暂时无法加载。请从 GitHub 仓库检查已完成的审计材料。';});
