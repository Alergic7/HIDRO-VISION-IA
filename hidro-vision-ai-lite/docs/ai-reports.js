(() => {
 'use strict';
 const $=id=>document.getElementById(id);
 let comparison=null,configured=false,busy=false;
 const states={sending:'Solicitud en curso; verifica Make si se interrumpió.',accepted_by_make:'Recibido por Make; correo sin confirmar.',sent_confirmed:'Make confirmó el envío; entrega en bandeja no verificada.',unknown:'Resultado incierto; revisa Make antes de reenviar.',rejected:'Rechazado por Make; revisa el historial.',not_sent:'Sin enviar.'};
 async function api(path,data){const r=await fetch('/api/platform/'+path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json','X-Hidro-Client':'local'}:{},body:data?JSON.stringify(data):undefined,cache:'no-store'});if(!r.headers.get('content-type')?.includes('application/json'))throw Error('Reinicia el servidor para cargar la integración de IA.');const value=await r.json();if(!r.ok)throw Error(value.error||'No se pudo completar la operación.');return value;}
 function message(text){$('aiMessage').textContent=text;}
 async function refreshConfig(){const c=await api('integrations');configured=c.openai_configured;$('integrationStatus').textContent=`OpenAI: ${configured?'configurado ('+c.model+')':'falta clave y modelo'}. Make: ${c.make_configured?'webhook configurado':'falta webhook'}. ${c.note}`;$('createAiReport').disabled=busy||!comparison||!configured;}
 async function refreshDeliveries(){
  if(!comparison)return;const current=comparison;
  const [reports,deliveries]=await Promise.all([api('reports?comparison='+current),api('deliveries?comparison='+current)]);
  if(comparison!==current)return;
  const box=$('reportDeliveries');box.replaceChildren();
  reports.forEach(r=>{const row=document.createElement('p'),a=document.createElement('a'),button=document.createElement('button'),label=document.createElement('span');a.textContent='PDF · '+new Date(r.created).toLocaleString('es-PE');a.href=r.url;a.target='_blank';a.rel='noopener';const d=deliveries.find(v=>v.report===r.id);label.textContent=' '+(d?states[d.state]||d.state:'Sin enviar.');button.textContent='Enviar PDF por Make';button.className='secondary';button.disabled=!!d;button.onclick=async()=>{button.disabled=true;try{const sent=await api('report-send',{report:r.id});message(sent.message);await refreshDeliveries();}catch(e){message(e.message);button.disabled=false;}};row.append(a,label,document.createElement('br'),button);box.append(row);});
 }
 window.addEventListener('hidro:result',e=>{comparison=e.detail.download?.match(/\/data\/([a-f0-9]{32})\//)?.[1]||null;message('');refreshConfig().catch(e=>message(e.message));refreshDeliveries().catch(e=>message(e.message));});
 window.addEventListener('DOMContentLoaded',()=>{
  $('refreshIntegrations').onclick=()=>{refreshConfig().catch(e=>message(e.message));refreshDeliveries().catch(e=>message(e.message));};
  $('createAiReport').onclick=async()=>{if(!comparison||busy)return;busy=true;$('createAiReport').disabled=true;const selected=comparison;message('OpenAI está analizando la evidencia y redactando el informe de dos páginas…');try{const report=await api('report-ai',{comparison:selected,send_make:$('sendAiReport').checked});if(comparison===selected){message('PDF de dos páginas generado. '+(report.delivery?.message||'Guardado localmente, sin envío.'));window.dispatchEvent(new Event('hidro:reports-updated'));await refreshDeliveries();}}catch(e){message(e.message);}finally{busy=false;$('createAiReport').disabled=!comparison||!configured;}};
  refreshConfig().catch(e=>message(e.message));
 });
})();
