import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from pypdf import PdfReader
import ai_reports as ai
import platform_store as store

CONTEXT={'campaigns':['Enero 2026','Julio 2026'],'tramo_m':[0,1200],'selected_stations':[0,600,1200],
         'findings':[],'total_findings':0,'weather':{'references':[],'unavailable':True}}
TEXT={key:'Prueba simulada: la evidencia requiere contraste en campo. No hay registros suficientes para atribuir causas.' for key in ai.LIMITS}
CONFIG={'OPENAI_API_KEY':'test-secret','OPENAI_MODEL':'gpt-4o','MAKE_WEBHOOK_URL':'https://hook.us1.make.com/test-hook'}

class AiReportsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old=(store.STORE,store.DB)
        store.STORE=Path(self.temp.name);store.DB=store.STORE/'platform.sqlite3'
        self.ident='a'*32;(store.STORE/self.ident).mkdir()
    def tearDown(self):
        store.STORE,store.DB=self.old;self.temp.cleanup()
    def generate(self):
        with patch.object(ai,'config',return_value=CONFIG),patch.object(ai,'evidence',return_value=(CONTEXT,[])),patch.object(ai,'analyze',return_value=(TEXT,{'model':'test-model'})):
            return ai.make_report({'comparison':self.ident})
    def test_two_pages_and_traceability(self):
        r=self.generate();p=ai.evidence_path(r['url'])
        pdf=PdfReader(p);self.assertEqual(len(pdf.pages),2)
        text='\n'.join(page.extract_text() for page in pdf.pages)
        self.assertIn('Precipitación',text);self.assertIn('Anomalías',text)
        self.assertIn('Enero 2026',text);self.assertIn('Julio 2026',text)
        self.assertEqual(json.loads(p.with_suffix('.json').read_text(encoding='utf-8'))['analysis'],TEXT)
    def test_missing_config_no_network(self):
        with patch.object(ai,'config',return_value={}),patch.object(ai,'post_json') as network:
            with self.assertRaisesRegex(ValueError,'Configura OpenAI'):ai.make_report({'comparison':self.ident})
            network.assert_not_called()
        with patch.object(ai,'config',return_value={'OPENAI_API_KEY':'secret','OPENAI_MODEL':'m'}):
            self.assertNotIn('secret',json.dumps(ai.status()))
    def test_make_attachment_recipient_and_duplicate(self):
        r=self.generate()
        with patch.object(ai,'config',return_value=CONFIG),patch.object(ai,'post_json',return_value=(200,b'Accepted')) as network:
            first=ai.send_report({'report':r['id'],'to':'unapproved@example.com'})
            self.assertEqual(first['state'],'accepted_by_make')
            body=network.call_args.args[1]
            self.assertEqual(body['to'],ai.RECIPIENT)
            self.assertTrue(base64.b64decode(body['attachment']['base64']).startswith(b'%PDF'))
            self.assertNotIn('test-secret',json.dumps(body))
            self.assertEqual(ai.send_report({'report':r['id']})['state'],'accepted_by_make')
            self.assertEqual(network.call_count,1)
    def test_timeout_no_automatic_retry(self):
        r=self.generate()
        with patch.object(ai,'config',return_value=CONFIG),patch.object(ai,'post_json',side_effect=TimeoutError) as network:
            self.assertEqual(ai.send_report({'report':r['id']})['state'],'unknown')
            self.assertEqual(ai.send_report({'report':r['id']})['state'],'unknown')
            self.assertEqual(network.call_count,1)
    def test_confirmed_send_requires_matching_receipt(self):
        r=self.generate()
        reply=json.dumps({'status':'sent','event_id':r['id'],'message_id':'gmail-test'}).encode()
        with patch.object(ai,'config',return_value=CONFIG),patch.object(ai,'post_json',return_value=(200,reply)):
            self.assertEqual(ai.send_report({'report':r['id']})['state'],'sent_confirmed')
    def test_response_refusal_and_incomplete(self):
        for status in ('incomplete','failed','completed'):
            response={'status':status,'output':[{'content':[{'type':'refusal','refusal':'test'}]}]}
            with patch.object(ai,'post_json',return_value=(200,json.dumps(response).encode())):
                with self.assertRaises(ValueError):ai.analyze(CONTEXT,[],CONFIG)
        with patch.object(ai,'post_json',side_effect=HTTPError('https://api.openai.com',401,'secret',{},None)):
            with self.assertRaisesRegex(ValueError,'HTTP 401'):ai.analyze(CONTEXT,[],CONFIG)
    def test_structured_response_and_limits(self):
        response={'status':'completed','id':'response-test','output':[{'content':[{'type':'output_text','text':json.dumps(TEXT)}]}]}
        with patch.object(ai,'post_json',return_value=(200,json.dumps(response).encode())) as network:
            data,metadata=ai.analyze(CONTEXT,[],CONFIG)
            self.assertEqual(data,TEXT);self.assertEqual(metadata['response_id'],'response-test')
            self.assertFalse(network.call_args.args[1]['store'])
        response['output'][0]['content'][0]['text']=json.dumps({**TEXT,'resumen':'x'*651})
        with patch.object(ai,'post_json',return_value=(200,json.dumps(response).encode())):
            with self.assertRaises(ValueError):ai.analyze(CONTEXT,[],CONFIG)
    def test_maximum_text_fits_two_pages(self):
        data={k:('La observación requiere inspección y contraste con las mediciones. '*100)[:n] for k,n in ai.LIMITS.items()}
        target=store.STORE/'layout.pdf'
        ai.render_pdf(target,data,CONTEXT,{'model':'gpt-4o'},'2026-10-26T00:00:00Z')
        self.assertEqual(len(PdfReader(target).pages),2)
    def test_webhook_restrictions_and_paths(self):
        for url in ['http://hook.make.com/x','https://example.com/x','https://hook.make.com.evil.com/x','https://user@hook.make.com/x','https://hook.make.com:444/x']:
            self.assertFalse(ai.webhook_valid(url))
        self.assertTrue(ai.webhook_valid(CONFIG['MAKE_WEBHOOK_URL']))
        with self.assertRaises(ValueError):ai.evidence_path('/data/../../secret')

if __name__=='__main__':unittest.main()
