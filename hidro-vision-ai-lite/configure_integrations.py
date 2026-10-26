"""Interactive local-only configuration; never prints credentials."""
import getpass
import json
from pathlib import Path
from urllib.parse import urlparse
import re

def main():
    target=Path(__file__).with_name('settings.local.json')
    values=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    print('HIDRO-VISION | OpenAI y Make. Enter conserva el valor existente.')
    print('Las credenciales se guardan solo en settings.local.json. No compartas ese archivo.')
    for key,label in [('OPENAI_API_KEY','Clave API de OpenAI'),('MAKE_WEBHOOK_URL','URL del webhook de Make'),('MAKE_API_KEY','Clave adicional de Make (opcional)')]:
        value=getpass.getpass(label+': ').strip()
        if value:values[key]=value
    model=input('Modelo de OpenAI ['+values.get('OPENAI_MODEL','gpt-4o')+']: ').strip()
    values['OPENAI_MODEL']=model or values.get('OPENAI_MODEL','gpt-4o')
    hook=values.get('MAKE_WEBHOOK_URL','')
    if hook:
        p=urlparse(hook)
        if not (p.scheme=='https' and re.fullmatch(r'hook(?:\.[a-z0-9-]+)?\.make\.com',p.hostname or '') and not p.username and not p.password and p.port in (None,443) and len(p.path)>1 and not p.query and not p.fragment):
            raise ValueError('Usa la URL HTTPS original de Custom webhook en Make. No se guardó la configuración.')
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(values,indent=2),encoding='utf-8');temp.replace(target)
    print('Configuración guardada. Destinatario: alexandra.colan.7@gmail.com. No se realizó ningún envío ni llamada a OpenAI.')

if __name__=='__main__':main()
