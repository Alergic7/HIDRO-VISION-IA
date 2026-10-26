"""Persistent workflow: campaigns, reviewed findings, reports and alert outbox.

No external service is called by this module. Criticality is assigned by a
named reviewer, never inferred from the RGB difference threshold.
"""
from pathlib import Path
import sqlite3, json, re, uuid, hashlib
from datetime import datetime, timezone
from contextlib import contextmanager
from processor import STORE, read_campaign, check, public

DB = STORE / 'platform.sqlite3'
TYPES = {
    'enrocado': 'Posible desplazamiento del enrocado',
    'erosion': 'Posible erosión del talud',
    'colmatacion': 'Posible colmatación',
    'deformacion': 'Posible asentamiento o deformación',
    'grietas': 'Posibles grietas',
    'agua': 'Menor superficie de agua visible',
    'vegetacion': 'Mayor cobertura vegetal visible',
    'dragado': 'Indicios de intervención / posible dragado',
    'pie': 'Revisar el pie del dique',
    'sin_cambio': 'Sin cambio relevante',
}
LEVELS = {'seguimiento':'Seguimiento', 'prioritaria':'Inspección prioritaria', 'urgente':'Alerta urgente'}

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect():
    db=sqlite3.connect(DB, timeout=30)
    db.row_factory=sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY, month INTEGER, year INTEGER, name TEXT NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS findings(id TEXT PRIMARY KEY, comparison TEXT NOT NULL, station REAL NOT NULL, category TEXT NOT NULL, level TEXT NOT NULL, evidence TEXT NOT NULL, rationale TEXT NOT NULL, reviewer TEXT NOT NULL, verified INTEGER NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, finding TEXT NOT NULL, record TEXT NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, comparison TEXT NOT NULL, url TEXT NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY, finding TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL, created TEXT NOT NULL);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()

def result_path(ident):
    check(isinstance(ident,str) and bool(re.fullmatch('[a-f0-9]{32}',ident)), 'Comparación no válida.')
    p=STORE/ident/'result.json'
    check(p.is_file(), 'No se encontró la comparación.')
    return p

def read_result(ident):
    return json.loads(result_path(ident).read_text(encoding='utf8'))

def station_ref(result, station):
    check(isinstance(station,(float,int)), 'Progresiva no válida.')
    ref=next((r for r in result['references'] if abs(r['station']-station)<.001),None)
    check(ref is not None, 'La progresiva no pertenece a esta comparación.')
    return ref

def sync_campaigns():
    months=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    with connect() as db:
        for p in STORE.glob('*/campaign.json'):
            c=json.loads(p.read_text(encoding='utf8'))
            if c['name'].upper().startswith('PRUEBA'):continue
            month=next((i+1 for i,m in enumerate(months) if m in c['name'].lower()),None)
            year=re.search(r'20\d{2}',c['name'])
            db.execute('INSERT OR IGNORE INTO campaigns VALUES(?,?,?,?,?)',
                       (c['id'],month,int(year[0]) if year else None,c['name'],datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()))

def campaigns():
    sync_campaigns()
    with connect() as db:rows=[dict(r) for r in db.execute('SELECT * FROM campaigns ORDER BY year DESC,month DESC,created DESC')]
    output=[]
    for row in rows:
        try:c=read_campaign(row['id'])
        except (OSError,ValueError):continue
        row.update(crs=c['crs'],files={'VIDEO':2,'ORTOFOTO':1,'XML':1,'PLANO_OTROS':len(c['plans'])})
        output.append(row)
    return output

def update_campaign(payload):
    ident=payload.get('id');c=read_campaign(ident)
    month,year=int(payload.get('month',0)),int(payload.get('year',0))
    check(1<=month<=12 and 2000<=year<=2100,'Indica un mes y año válidos.')
    sync_campaigns()
    with connect() as db:db.execute('UPDATE campaigns SET month=?,year=? WHERE id=?',(month,year,ident))
    return {'id':ident,'month':month,'year':year,'name':c['name']}

def comparisons():
    rows=[]
    for p in STORE.glob('*/result.json'):
        r=json.loads(p.read_text(encoding='utf8'))
        if any(m['name'].upper().startswith('PRUEBA') for m in r['months']):continue
        ids=[m['video'].split('/')[2] for m in r['months']]
        rows.append(dict(id=p.parent.name,ids=ids,months=[m['name'] for m in r['months']],url=public(p),created=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()))
    return sorted(rows,key=lambda r:r['created'],reverse=True)

def findings(comparison=None):
    with connect() as db:
        query='SELECT * FROM findings'+(' WHERE comparison=?' if comparison else '')+' ORDER BY updated DESC'
        return [dict(r) for r in db.execute(query,(comparison,) if comparison else ())]

def save_finding(payload):
    result=read_result(payload.get('comparison'))
    ref=station_ref(result,payload.get('station'))
    category=payload.get('category');level=payload.get('level')
    check(category in TYPES,'Categoría de hallazgo no válida.')
    check(level in LEVELS,'Nivel de atención no válido.')
    evidence=str(payload.get('evidence','')).strip()
    rationale=str(payload.get('rationale','')).strip()
    reviewer=str(payload.get('reviewer','')).strip()
    check(10<=len(evidence)<=4000,'Describe la evidencia (entre 10 y 4000 caracteres).')
    check(10<=len(rationale)<=4000,'Explica el motivo del nivel de atención (entre 10 y 4000 caracteres).')
    check(2<=len(reviewer)<=150,'Indica quién revisa el hallazgo.')
    check(any(i.get('coverage',0)>0 for i in ref['images']) or any(v.get('url') for v in ref['videos']), 'La progresiva no dispone de imágenes válidas.')
    ident=payload.get('id') or uuid.uuid4().hex
    check(bool(re.fullmatch('[a-f0-9]{32}',ident)),'Identificador no válido.')
    verified=bool(payload.get('verified',False))
    stamp=now()
    with connect() as db:
        prior=db.execute('SELECT * FROM findings WHERE id=?',(ident,)).fetchone()
        if prior:check(prior['comparison']==payload['comparison'] and abs(prior['station']-ref['station'])<.001,'No se puede reasignar un hallazgo a otra evidencia.')
        created=prior['created'] if prior else stamp
        record=dict(id=ident,comparison=payload['comparison'],station=ref['station'],category=category,level=level,evidence=evidence,rationale=rationale,reviewer=reviewer,verified=int(verified),created=created,updated=stamp)
        db.execute('INSERT OR REPLACE INTO findings VALUES(?,?,?,?,?,?,?,?,?,?,?)',tuple(record.values()))
        db.execute('INSERT INTO reviews VALUES(?,?,?,?)',(uuid.uuid4().hex,ident,json.dumps(record,ensure_ascii=False),stamp))
    return record

def model_status():
    rows=findings()
    counts={k:sum(r['category']==k and r['verified'] for r in rows) for k in TYPES}
    with connect() as db:revisions=db.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
    return dict(mode='collecting_reviewed_examples',trained=False,findings=len(rows),verified=sum(bool(r['verified']) for r in rows),revisions=revisions,by_category=counts,
                message='Banco de ejemplos supervisados. Aún no hay un modelo de anomalías entrenado ni precisión validada.')

def training_export():
    rows=[]
    for finding in findings():
        result=read_result(finding['comparison']);ref=station_ref(result,finding['station'])
        rows.append(dict(**finding,months=result['months'],images=ref['images'],videos=ref['videos'],crs=result['crs']))
    return {'schema':'hidro-vision-training-v1','exported_at':now(),'examples':rows,'note':'Etiquetas humanas; separar campañas y ubicaciones entre entrenamiento y evaluación. No son predicciones de un modelo.'}

def prepare_alert(payload):
    with connect() as db:
        row=db.execute('SELECT * FROM findings WHERE id=?',(payload.get('finding'),)).fetchone()
        check(row is not None,'Hallazgo no encontrado.')
        finding=dict(row)
        result=read_result(finding['comparison'])
        body=dict(event='hidro_vision.reviewed_finding',schema_version=1,finding=finding,
                  category=TYPES[finding['category']],attention=LEVELS[finding['level']],
                  months=[m['name'] for m in result['months']],
                  report_url=payload.get('report_url'),
                  delivery_note='Preparado localmente. Enviar requiere Make y destinatarios configurados. Las rutas locales no son accesibles desde Make.')
        ident=uuid.uuid4().hex
        db.execute('INSERT INTO alerts VALUES(?,?,?,?,?)',(ident,finding['id'],json.dumps(body,ensure_ascii=False),'prepared_not_sent',now()))
    return dict(id=ident,state='prepared_not_sent',payload=body)

def alert_list():
    with connect() as db:return [dict(r) for r in db.execute('SELECT id,finding,state,created FROM alerts ORDER BY created DESC')]

def report_list(comparison):
    with connect() as db:return [dict(r) for r in db.execute('SELECT * FROM reports WHERE comparison=? ORDER BY created DESC',(comparison,))]

def make_report(comparison):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as PDFImage, PageBreak, KeepTogether
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from xml.sax.saxutils import escape
    result=read_result(comparison)
    rows=findings(comparison)
    ident=uuid.uuid4().hex
    folder=STORE/comparison/'reports';folder.mkdir(exist_ok=True)
    target=folder/(ident+'.pdf')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyHidro',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=9,textColor=colors.HexColor('#233d4a')))
    styles['Title'].textColor=colors.HexColor('#123b4a')
    def text(value,style='BodyHidro'):return Paragraph(escape(str(value)).replace('\n','<br/>'),styles[style])
    story=[text('HIDRO-VISION AI','Title'),text('Informe de comparación y revisión técnica','Heading2'),text(' / '.join(m['name'] for m in result['months'])),text('Generado: '+now()),text('Documento elaborado con plantilla estructurada y evidencias. No se ha utilizado un LLM ni un detector entrenado de anomalías.'),Spacer(1,12),text('Resumen de la comparación','Heading2'),text(f"Sistema de coordenadas: {result['crs']}. Tramo: {result['start']:.2f} a {result['end']:.2f} m. Sectores: {len(result['sectors'])}. Referencias: {len(result['references'])}. Hallazgos revisados: {len(rows)}."),text('Los niveles de atención fueron asignados por el revisor. La diferencia RGB es exploratoria; no mide pérdida de material ni confirma erosión, socavación o riesgo para viviendas.')]
    for warning in result.get('warnings',[]):story.append(text(warning))
    for level,label in LEVELS.items():story.append(text(f"{label}: {sum(r['level']==level for r in rows)} hallazgos."))
    if not rows:story.append(text('No se han registrado hallazgos revisados. Esto no certifica la ausencia de anomalías. Se incluyen las primeras referencias con video como evidencia de la comparación.'))
    selections=[(r,station_ref(result,r['station'])) for r in rows]
    if not selections:selections=[(None,r) for r in result['references'] if all(v.get('url') for v in r['videos'])][:3]
    def local(url):
        check(url.startswith('/data/'),'Ruta de evidencia no válida.')
        p=(STORE/url[6:]).resolve()
        check(p.is_relative_to(STORE.resolve()),'Ruta de evidencia fuera de la carpeta local.')
        return p
    for finding,ref in selections:
        story.append(PageBreak())
        story.extend([text(f"Progresiva del dron: {ref['station']:.2f} m",'Heading2'),text(TYPES[finding['category']] if finding else 'Evidencia de referencia')])
        if finding:
            story.extend([text('Nivel de atención: '+LEVELS[finding['level']]),text('Revisor: '+finding['reviewer']),text('Verificación de campo: '+('registrada por el revisor' if finding['verified'] else 'pendiente')),text('Observación: '+finding['evidence']),text('Justificación: '+finding['rationale'])])
        cells=[]
        for i,v in enumerate(ref['videos']):
            if v.get('url'):
                image=PDFImage(str(local(v['url'])))
                image.drawHeight=image.imageHeight/image.imageWidth*235;image.drawWidth=235
                cells.append([text(result['months'][i]['name']),image,text(f"Tiempo {v['time']:.2f} s. Progresiva proyectada {v['station']:.2f} m.")])
            else:
                image=PDFImage(str(local(ref['images'][i]['url'])),width=235,height=235)
                cells.append([text(result['months'][i]['name']+' - ortofoto'),image,text('Sin fotograma cercano; se muestra la ortofoto.')])
        table=Table([[cells[0],cells[1]]],colWidths=[247,247]);table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),12)]));story.append(table)
        note=ref.get('observation',{}).get('summary')
        if note:story.append(text('Lectura visual registrada: '+note))
        story.append(text('La posición del dron no localiza toda la superficie visible. Contrastar con el plano, niveles de agua e inspección de campo.'))
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#48606b'));canvas.drawString(45,28,'HIDRO-VISION AI | Evidencias y revisión humana');canvas.drawRightString(A4[0]-45,28,str(doc.page))
    SimpleDocTemplate(str(target),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=42,bottomMargin=48).build(story,onFirstPage=footer,onLaterPages=footer)
    url=public(target)
    with connect() as db:db.execute('INSERT INTO reports VALUES(?,?,?,?)',(ident,comparison,url,now()))
    return dict(id=ident,url=url,mode='structured_template',findings=len(rows))
