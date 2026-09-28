#!/usr/bin/env python3
"""Render reviewable voice lists and local audio links from synthesis results."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--historical-inventory',type=Path,required=True);a=p.parse_args()
 rows=json.loads((a.package/'catalog.json').read_text());manifest=json.loads((a.package/'audio/manifest.json').read_text());by={(r['id'],r['lang']):r for r in manifest}
 fixed=[r for r in rows if r['kind']!='dynamic'];dynamic=[r for r in rows if r['kind']=='dynamic']
 lines=['# Catálogo de voz Cruzr S2: chino, español e inglés','',
 '22-09-2026, Europe/Madrid. VOICE-ES-01. Preparado en PC; **no instalado en el robot**.','',
 f'Cobertura: {len(fixed)-1} frases fijas y {len(dynamic)} variables TtsClient en el snapshot de tareas del 16-09, más el aviso de arranque local ya inglés. No equivale a todos los mensajes compilados del robot ni confirma qué tareas están activas. El robot fue apagado/desconectado durante la consulta actual; el operador lo confirmó.','',
 'Se han generado WAV PCM de 16 bits, mono, 16 kHz y MP3 con voces sintéticas Elvira (español de España) y Sonia (inglés británico). La síntesis usa Edge TTS desde el PC. Los textos traducidos se enviaron al servicio de síntesis; no se enviaron grabaciones del robot. Los WAV tienen formato candidato para reproducción por archivo; compatibilidad con el reproductor nativo pendiente.','',
 '**Escucha:** no se copiaron ni escucharon los originales del robot. Sus nombres proceden del inventario anterior. Los audios nuevos se verifican por decodificación, duración y señal no nula; eso no es una escucha ni revisión humana de pronunciación.','',
 '## Frases fijas y audios preparados','',
 'Traducciones propuestas. Los números finales de pruebas se conservan. Frases parciales como «开始执行第» deben recomponerse con su número/sufijo para que el TTS inglés resulte natural. «下桩充电» combina salir de la estación y cargar en el original; se ha interpretado como salida, pendiente de confirmar el evento. «前坐/后坐» requiere validar el nombre exacto de la maniobra.','',
 '| ID / origen | Chino | Español | Inglés para TTS | Audios |','|---|---|---|---|---|']
 for r in fixed:
  links=[]
  for lang in ['es','en']:
   item=by.get((r['id'],lang),{})
   if 'wav' in item:links.append(f'[{lang.upper()}]({item["wav"]})')
   else:links.append(lang+': PENDIENTE')
  src=r['sources'][0];link=f'[{r["id"]}](../../{src})'
  vals=[link,r['zh'] or '(arranque local, original inglés)',r['es'],r['en'],' / '.join(links)]
  lines.append('| '+' | '.join(v.replace('|','\\|') for v in vals)+' |')
 lines+=['','## Textos dinámicos: no sustituir por una grabación fija','',
 'Estos campos pueden contener números, booleanos o mensajes de error generados en ejecución. Se conservan intactos en las copias inglesas. Sus productores deben localizarse y traducirse por código/plantilla, manteniendo valores y significado; no basta con cambiar language=en.','',
 '| Variable | Fuente de ejemplo |','|---|---|']
 for r in dynamic:lines.append('| `'+r['zh']+'` | ['+Path(r['sources'][0]).name+'](../../'+r['sources'][0]+') |')
 audio=set()
 for line in a.historical_inventory.read_text().splitlines():
  try:d=json.loads(line)
  except ValueError:continue
  audio.update(p for p in d.get('files','').splitlines() if p.startswith('/opt/') and p.endswith(('.wav','.mp3','.ogg')))
 lines+=['','## Archivos de audio originales localizados: escucha pendiente','',
 'Inventario leído el 22-09 antes de la desconexión; 22 rutas únicas. Las categorías siguientes son inferencias por ruta/nombre, no transcripciones. No sustituir efectos o música por voz sin identificar su función.','',
 '| Ruta en Vision | Clasificación provisional | Estado |','|---|---|---|']
 for p in sorted(audio):
  name=Path(p).name
  kind=('Posible respuesta «Aquí estoy»; confirmar contenido' if name.startswith('在的-') else 'Muestra de voz; contenido desconocido' if '/demo/' in p else 'Posible música o pista de fondo' if '/bgm/' in p or '/back/' in p else 'Posible efecto/aviso no verbal; comprobar')
  lines.append('| `'+p+'` | '+kind+' | Sin copia ni escucha |')
 lines+=['','## Qué se puede usar y qué queda pendiente','',
 '- Los WAV españoles y sus equivalentes ingleses están listos para escuchar en el PC. Reproducción directa en el robot pendiente de verificar endpoint, contrato de archivo y formato; no se ha reproducido ningún aviso allí.',
 '- `tts-goals-en.json` contiene objetivos de texto con `language=en`, basados en el contrato usado por el aviso local de arranque. Deben descubrirse servidor y tipo actuales antes de enviar; el catálogo no ejecuta acciones.',
 '- `xml_en/` contiene copias de 57 XML: sólo cambia el literal `tts`. Las variables y órdenes de movimiento se conservan. Son borradores; TtsClient puede tener configuración de idioma separada, y ejecutar esos XML puede mover el robot.',
 '- Faltan los avisos embebidos en binarios/configuraciones no capturadas, conversación libre, transcripción de WAV y asociación comprobada evento→audio. El inventario remoto se puede retomar sin reproducir ni modificar archivos.',
 '', '## Archivos y reproducción del paquete','',
 f'Paquete privado: `{a.package.resolve()}`. Audios/binarios fuera de Git; enlaces anteriores son locales a este PC.',
 '', '- [Traducciones editables](traducciones.tsv).',
 '- [Inventario JSON con todas las fuentes](catalogo.json).',
 '- [Objetivos TTS ingleses, sin ejecución](tts-goals-en.json).',
 '- [Inventariador de sólo lectura](../../scripts/voice/inventory_robot_voice.py).',
 '- [Generador de catálogo y XML](../../scripts/voice/build_voice_catalog.py).',
 '- [Síntesis ES/EN](../../scripts/voice/synthesize_catalog.py).',
 '- [Generador de esta lista](../../scripts/voice/render_voice_catalog.py).',
 '', 'Receta (desde la raíz; sustituir SALIDA por una ruta privada):','', '```bash',
 'python3 scripts/voice/build_voice_catalog.py --output SALIDA',
 '../Humanoide-vla-evidence/voice-tools-venv/bin/python scripts/voice/synthesize_catalog.py --catalog SALIDA/catalog.json --output SALIDA/audio',
 'python3 scripts/voice/render_voice_catalog.py --package SALIDA --historical-inventory ../Humanoide-vla-evidence/20260922T114535Z_VOICE_INVENTORY/inventory.jsonl',
 '# Cuando vuelva la conexión, lectura de archivos sin reproducción:',
 'python3 scripts/voice/inventory_robot_voice.py --output /RUTA/PRIVADA/NUEVA',
 '```','',
 'Herramientas instaladas únicamente en el entorno privado `../Humanoide-vla-evidence/voice-tools-venv`; versiones en la evidencia. No se modificó SDK original, servicios, tareas activas, idiomas ni voces del robot. Reversión: retirar los archivos nuevos del PC y su entorno/paquete privado; no hay rollback remoto.']
 out=ROOT/'docs/voice';(out/'CATALOGO_VOZ_ES_EN.md').write_text('\n'.join(lines)+'\n');(out/'catalogo.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(out/'tts-goals-en.json').write_bytes((a.package/'tts-goals-en.json').read_bytes())
 print('Rendered',len(fixed),'fixed/boot',len(dynamic),'dynamic',len(audio),'original audio paths')
if __name__=='__main__':main()
