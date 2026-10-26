(() => {
 'use strict';
 const by=id=>document.getElementById(id);
 const types={enrocado:'Posible desplazamiento del enrocado',erosion:'Posible erosión del talud',colmatacion:'Posible colmatación',deformacion:'Posible asentamiento o deformación',grietas:'Posibles grietas',agua:'Menor superficie de agua visible',vegetacion:'Mayor cobertura vegetal visible',dragado:'Indicios de intervención / posible dragado',pie:'Revisar el pie del dique',sin_cambio:'Sin cambio relevante'};
 const levels={seguimiento:'Seguimiento',prioritaria:'Inspección prioritaria',urgente:'Alerta urgente'};
 let library=[],saved=[],active=null,comparison=null,reference=null,rows=[],editing=null,latestReport=null,refreshToken=0;
 const station=n=>`${Math.floor(n/1000)}+${(n%1000).toFixed(n%1?2:0).padStart(3,'0')}`;
 const months=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
 const label=c=>c.month&&c.year?`${months[c.month-1]} ${c.year} · ${c.name}`:c.name;
 function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
 async function request(path,payload){const r=await fetch('/api/platform/'+path,{method:payload?'POST':'GET',headers:payload?{'Content-Type':'application/json','X-Hidro-Client':'local'}:{},body:payload?JSON.stringify(payload):undefined,cache:'no-store'});if(!r.headers.get('content-type')?.includes('application/json'))throw Error('El servidor no tiene cargada esta versión. Reinicia INICIAR_HIDRO_VISION.cmd y recarga la página.');const value=await r.json();if(!r.ok)throw Error(value.error||'No se pudo completar la operación.');return value;}
 function status(id,text,error=false){by(id).textContent=text;by(id).className=error?'error':'';}
 function link(url,text,cls){const a=node('a',text,cls);a.href=url;return a;}
 function resultLink(r){return '/?resultado='+encodeURIComponent(r.url)+'#planta';}
 function selectCampaigns(){
  campaigns[0]=library.find(c=>c.id===by('libraryA').value)||null;
  campaigns[1]=library.find(c=>c.id===by('libraryB').value)||null;
  ready();
  if(campaigns[0]&&campaigns[1]&&campaigns[0].id===campaigns[1].id){by('run').disabled=true;status('processing','Selecciona dos campañas diferentes.',true);return;}
  status('processing','');
 }
 async function refreshLibrary(){
  const [all,comparisons]=await Promise.all([request('campaigns'),request('comparisons')]);
  saved=comparisons;const seen=new Set();library=all.filter(c=>{const key=[c.name,c.month,c.year].join('|');if(seen.has(key))return false;seen.add(key);return true;});
  by('historyCount').textContent=`${library.length} campañas disponibles. Las cargas repetidas del mismo mes y nombre muestran la versión más reciente.`;
  const history=by('campaignHistory');history.replaceChildren();
  if(!library.length)history.append(node('p','Tu primera campaña aparecerá aquí al validar el ZIP.','empty-state'));
  library.forEach(c=>{const row=node('div',undefined,'history-row'),left=node('div');left.append(node('strong',label(c)),node('small',`${c.crs} · Video + SRT · Ortofoto · XML · ${c.files.PLANO_OTROS} referencias`));row.append(left,node('span','✓ Validada','badge'));history.append(row);});
  ['libraryA','libraryB'].forEach(id=>{const selected=by(id).value;by(id).replaceChildren(new Option('Selecciona una campaña',''),...library.map(c=>new Option(label(c),c.id)));if(library.some(c=>c.id===selected))by(id).value=selected;});
  by('savedComparisons').replaceChildren();
  if(saved.length){by('savedComparisons').append(node('h3','Comparaciones ya procesadas'));saved.slice(0,6).forEach(r=>by('savedComparisons').append(link(resultLink(r),r.months.join(' ↔ ')+' · Abrir sin volver a procesar')));}
  selectCampaigns();
 }
 async function register(file){
  if(!file)return;if(!file.name.toLowerCase().endsWith('.zip')){status('statusA','Selecciona un archivo ZIP.',true);return;}
  const month=Number(by('campaignMonth').value),year=Number(by('campaignYear').value);
  if(!Number.isInteger(year)||year<2000||year>2100){status('statusA','Indica un año entre 2000 y 2100.',true);return;}
  working=true;by('zipA').disabled=true;by('run').disabled=true;by('zipChecks').classList.remove('valid');status('statusA','Validando y registrando '+file.name+'…');
  try{const c=await upload(file,0);await request('campaign',{id:c.id,month,year});by('zipChecks').classList.add('valid');status('statusA',`${c.name}: campaña guardada. Las cuatro carpetas fueron verificadas.`);await refreshLibrary();const target=by('libraryA').value?'libraryB':'libraryA';by(target).value=c.id;selectCampaigns();}
  catch(e){status('statusA',e.message,true);}
  finally{working=false;by('zipA').disabled=false;selectCampaigns();}
 }
 function questions(){
  if(!active||!reference)return;
  by('findingScope').textContent=`Comparación ${active.months.map(m=>m.name).join(' ↔ ')} · Progresiva del dron ${station(reference.station)}. Cambia la progresiva en la sección de videos para revisar otra ubicación.`;
  const sector=active.sectors.find(s=>reference.station>=s.start&&reference.station<=s.end);
  const cards=[
   ['Cambio visible',`¿Dónde conviene mirar primero?`,sector?`En el sector ${station(sector.start)}–${station(sector.end)}, el ${sector.changed_pct}% de la cobertura común presenta diferencias de color en la vista reducida.`:'Compara la evidencia de esta progresiva.','Comprueba que el cambio no se explique por sombra, luz, perspectiva o desalineación.'],
   ['Agua y vegetación','¿Hay menos agua visible o más terreno expuesto?','Contrasta el ancho aparente del cauce mojado, las barras y la vegetación entre ambas fechas.','Menor superficie de agua no equivale a sequía: contrasta niveles, caudales y fechas de vuelo.'],
   ['Intervención','¿Aparecen indicios de dragado o movimiento de material?','Busca maquinaria, trazas de trabajo y cambios de forma. Una barra expuesta por sí sola no demuestra dragado.','Verifica partes de obra y levantamientos antes de atribuir la causa.'],
   ['Pie del dique','¿El canal se acerca al enrocado o se ve pérdida de apoyo?','Revisa contactos, posibles vacíos, desplazamiento de piedras o cambios de margen en la misma ubicación.','La socavación necesita comprobación del pie y del lecho; no se confirma por disminución del área libre.']
  ];
  by('questionCards').replaceChildren(...cards.map(([badge,title,body,verify])=>{const c=node('article',undefined,'question-card');c.append(node('span',badge,'badge'),node('h3',title),node('p',body),node('p',verify,'verify'));return c;}));
 }
 function resetForm(){editing=null;by('findingForm').reset();by('findingReviewer').value=localStorage.getItem('hidro-reviewer')||'';status('findingMessage','');}
 function edit(row){
  const i=active.references.findIndex(r=>Math.abs(r.station-row.station)<.001);
  if(i>=0){by('gpsStation').value=i;by('gpsStation').dispatchEvent(new Event('change'));}
  editing=row.id;by('findingCategory').value=row.category;by('findingLevel').value=row.level;by('findingEvidence').value=row.evidence;by('findingRationale').value=row.rationale;by('findingReviewer').value=row.reviewer;by('findingVerified').checked=!!row.verified;
  by('findingForm').scrollIntoView({behavior:'smooth',block:'start'});status('findingMessage','Editando un hallazgo guardado. Se conservará el historial de la revisión.');
 }
 async function refreshWorkflow(){
  if(!comparison)return;const token=++refreshToken;
  const [findings,model,reports,alerts]=await Promise.all([request('findings?comparison='+comparison),request('model'),request('reports?comparison='+comparison),request('alerts')]);
  if(token!==refreshToken)return;rows=findings;
  by('modelStatus').textContent=`${model.findings} hallazgos registrados · ${model.verified} verificados en campo · ${model.revisions} revisiones. ${model.message}`;
  by('findingList').replaceChildren();
  if(!rows.length)by('findingList').append(node('p','Aún no hay hallazgos registrados en esta comparación. Usa las preguntas para orientar la revisión y documenta lo que observas.','empty-state'));
  rows.forEach(row=>{const card=node('article',undefined,'finding-row'),body=node('div');body.append(node('h4',`${station(row.station)} · ${types[row.category]}`),node('span',levels[row.level],'pill'),node('p',row.evidence),node('p','Motivo: '+row.rationale),node('small',`${row.reviewer} · ${row.verified?'Verificado en campo':'Pendiente de campo'}`));const button=node('button','Revisar / corregir','secondary');button.onclick=()=>edit(row);card.append(body,button);by('findingList').append(card);});
  by('alertFinding').replaceChildren(new Option('Selecciona un hallazgo',''),...rows.map(r=>new Option(`${station(r.station)} · ${types[r.category]} · ${levels[r.level]}`,r.id)));
  by('prepareAlert').disabled=!rows.length;
  by('reportList').replaceChildren();reports.forEach(r=>{const a=link(r.url,'Abrir informe PDF · '+new Date(r.created).toLocaleString('es-PE'),'report-link');a.target='_blank';a.rel='noopener';by('reportList').append(a);});latestReport=reports[0]?.url||null;
  by('alertList').replaceChildren();alerts.filter(a=>rows.some(r=>r.id===a.finding)).slice(0,5).forEach(a=>by('alertList').append(node('p','Preparada, sin enviar · '+new Date(a.created).toLocaleString('es-PE'),'muted')));
 }
 window.addEventListener('hidro:reports-updated',()=>refreshWorkflow().catch(e=>status('reportMessage',e.message,true)));
 window.addEventListener('hidro:result',e=>{active=e.detail;comparison=active.download?.match(/\/data\/([a-f0-9]{32})\//)?.[1];resetForm();if(comparison)refreshWorkflow().catch(e=>status('findingMessage',e.message,true));});
 window.addEventListener('hidro:reference',e=>{reference=e.detail;resetForm();questions();});
 window.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('.workflow-strip a[href="#entrada"]').forEach(a=>a.addEventListener('click',()=>{if(by('entrada').hidden)by('back').click();}));
  document.querySelectorAll('.workflow-strip a:not([href="#entrada"])').forEach(a=>a.addEventListener('click',e=>{if(by('resultado').hidden){e.preventDefault();status('processing','Selecciona dos campañas o abre una comparación guardada para acceder a esta etapa.');by('processing').scrollIntoView({behavior:'smooth',block:'center'});}}));
  const today=new Date();by('campaignMonth').value=today.getMonth()+1;by('campaignYear').value=today.getFullYear();
  by('zipA').onchange=()=>register(by('zipA').files[0]);
  const drop=by('zipDrop');['dragenter','dragover'].forEach(type=>drop.addEventListener(type,e=>{e.preventDefault();drop.classList.add('dragging');}));['dragleave','drop'].forEach(type=>drop.addEventListener(type,e=>{e.preventDefault();drop.classList.remove('dragging');}));drop.addEventListener('drop',e=>{if(!working)register(e.dataTransfer.files[0]);});
  by('libraryA').onchange=selectCampaigns;by('libraryB').onchange=selectCampaigns;
  by('refreshHistory').onclick=()=>refreshLibrary().catch(e=>status('historyCount',e.message,true));
  by('findingCategory').replaceChildren(...Object.entries(types).map(([value,title])=>new Option(title,value)));
  by('clearFinding').onclick=resetForm;
  by('findingForm').onsubmit=async e=>{
   e.preventDefault();if(!comparison||!reference)return;
   const payload={comparison,station:reference.station,category:by('findingCategory').value,level:by('findingLevel').value,evidence:by('findingEvidence').value,rationale:by('findingRationale').value,reviewer:by('findingReviewer').value,verified:by('findingVerified').checked};if(editing)payload.id=editing;
   const button=e.target.querySelector('button[type=submit]');button.disabled=true;
   try{const row=await request('finding',payload);editing=row.id;try{localStorage.setItem('hidro-reviewer',payload.reviewer);}catch{}await refreshWorkflow();status('findingMessage','Hallazgo guardado con evidencia, revisor e historial de cambios.');}
   catch(error){status('findingMessage',error.message,true);}finally{button.disabled=false;}
  };
  by('createReport').onclick=async()=>{if(!comparison)return;by('createReport').disabled=true;status('reportMessage','Generando el informe con evidencias…');try{const r=await request('report',{comparison});await refreshWorkflow();status('reportMessage','Informe PDF disponible. Redacción estructurada, sin LLM.');}catch(e){status('reportMessage',e.message,true);}finally{by('createReport').disabled=false;}};
  by('prepareAlert').onclick=async()=>{const finding=by('alertFinding').value;if(!finding){status('alertMessage','Selecciona un hallazgo revisado.',true);return;}by('prepareAlert').disabled=true;try{const r=await request('alert',{finding,report_url:latestReport});by('alertPreview').textContent=JSON.stringify(r.payload,null,2);status('alertMessage','Alerta preparada y registrada. No se ha enviado ningún mensaje.');await refreshWorkflow();}catch(e){status('alertMessage',e.message,true);}finally{by('prepareAlert').disabled=!rows.length;}};
  by('exportTraining').onclick=async()=>{try{const r=await request('training');const url=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:'application/json'}));const a=link(url,'');a.download='hidro-vision-ejemplos-supervisados.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}catch(e){status('modelStatus',e.message,true);}};
  if(location.protocol!=='file:')refreshLibrary().catch(e=>status('historyCount','No se pudo cargar el historial: '+e.message,true));
 });
})();
