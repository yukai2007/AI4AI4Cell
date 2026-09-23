"""Minimal layout-only XML repair of the supplied editable framework slide.

Retains all author text, connectors, icons, shape colors and panel geometry.
Uses XML patching rather than reconstructing the PowerPoint. The original
archive is never overwritten. No scientific labels are changed here.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as E

SOURCE = Path('/liziqing/yukai/AI4AI4Cell/ai4ai4cell_editable_framework-1(2).pptx')
import argparse
import tempfile
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work-dir', type=Path)
parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'figures')
args = parser.parse_args()
WORK = args.work_dir or Path(tempfile.mkdtemp(prefix='ai4ai4cell-framework-'))
WORK.mkdir(parents=True, exist_ok=True)
DEST = WORK / 'framework_user_20260923_readable_original_labels.pptx'
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
for prefix, uri in NS.items():
    E.register_namespace(prefix, uri)


def pt(x): return str(round(x * 12700))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def original_text(root):
    return [node.text for node in root.findall('.//a:t', NS)]


def configure(shape, x=None, y=None, w=None, h=None, size=None, align=None):
    transform = shape.find('p:spPr/a:xfrm', NS)
    if transform is not None:
        off, extent = transform.find('a:off', NS), transform.find('a:ext', NS)
        for key, val, target in [('x', x, off), ('y', y, off), ('cx', w, extent), ('cy', h, extent)]:
            if val is not None: target.set(key, pt(val))
    body = shape.find('p:txBody/a:bodyPr', NS)
    if body is not None:
        body.set('wrap','none'); body.set('anchor','t')
    for paragraph in shape.findall('p:txBody/a:p', NS):
        prop = paragraph.find('a:pPr', NS)
        if prop is None:
            prop = E.Element('{'+NS['a']+'}pPr');paragraph.insert(0,prop)
        if align: prop.set('algn',align)
        old = prop.find('a:lnSpc', NS)
        if old is not None: prop.remove(old)
        spacing = E.SubElement(prop,'{'+NS['a']+'}lnSpc')
        E.SubElement(spacing,'{'+NS['a']+'}spcPct',{'val':'100000'})
        for key in ('spcBef','spcAft'):
            old=prop.find('a:'+key,NS)
            if old is not None:prop.remove(old)
            old=E.SubElement(prop,'{'+NS['a']+'}'+key)
            E.SubElement(old,'{'+NS['a']+'}spcPts',{'val':'0'})
        properties = paragraph.findall('a:r/a:rPr',NS)+paragraph.findall('a:endParaRPr',NS)
        for rp in properties:
            if size is not None:rp.set('sz',str(round(size*100)))
            for tag in ('latin','ea','cs'):
                font=rp.find('a:'+tag,NS)
                if font is None:font=E.SubElement(rp,'{'+NS['a']+'}'+tag)
                font.set('typeface','Carlito')


original_sha=sha(SOURCE)
with ZipFile(SOURCE) as archive:
    raw={name:archive.read(name) for name in archive.namelist()}
root=E.fromstring(raw['ppt/slides/slide1.xml'])
before=original_text(root)
shapes={sp.find('p:nvSpPr/p:cNvPr',NS).get('name'):sp for sp in root.findall('.//p:sp',NS)}
for sp in shapes.values():
    if sp.findall('.//a:t',NS):configure(sp)
changes={
 'Text 0':dict(x=20,y=12,w=680,h=25,size=21,align='ctr'),
 'Text 2':dict(x=30,y=49,w=340,h=21,size=17),
 'Text 3':dict(x=431,y=52,w=255,h=15,size=11,align='r'),
 'Text 5':dict(x=43,y=88,w=18,h=17,size=13),
 'Text 6':dict(x=61,y=88,w=88,h=17,size=13),
 'Text 10':dict(x=192,y=88,w=18,h=17,size=13),
 'Text 11':dict(x=210,y=88,w=91,h=17,size=13),
 'Text 15':dict(x=339,y=88,w=18,h=17,size=13),
 'Text 16':dict(x=357,y=88,w=96,h=17,size=12),
 'Text 20':dict(x=494,y=88,w=18,h=17,size=13),
 'Text 21':dict(x=512,y=88,w=99,h=17,size=12),
 'Text 38':dict(x=30,y=206,w=510,h=20,size=16),
 'Text 43':dict(x=251,y=240,w=280,h=20,size=14),
 'Text 44':dict(x=251,y=262,w=291,h=18,size=11),
 'Text 45':dict(x=286,y=293,w=174,h=14,size=11),
 'Text 47':dict(x=32,y=315,w=153,h=17,size=12,align='ctr'),
 'Text 59':dict(x=203,y=315,w=157,h=17,size=12,align='ctr'),
 'Text 71':dict(x=388,y=315,w=160,h=17,size=12,align='ctr'),
 'Text 49':dict(x=31,y=362,w=38,h=20,size=9,align='ctr'),
 'Text 52':dict(x=82,y=362,w=53,h=20,size=9,align='ctr'),
 'Text 55':dict(x=146,y=362,w=43,h=20,size=9,align='ctr'),
 'Text 61':dict(x=204,y=362,w=38,h=20,size=9,align='ctr'),
 'Text 64':dict(x=256,y=362,w=53,h=20,size=9,align='ctr'),
 'Text 67':dict(x=317,y=362,w=43,h=20,size=9,align='ctr'),
 'Text 73':dict(x=391,y=362,w=38,h=20,size=9,align='ctr'),
 'Text 76':dict(x=439,y=362,w=53,h=20,size=9,align='ctr'),
 'Text 79':dict(x=502,y=362,w=43,h=20,size=9,align='ctr'),
 'Text 89':dict(x=601,y=214,w=96,h=21,size=17,align='ctr'),
 'Text 92':dict(x=603,y=245,w=92,h=26,size=11,align='ctr'),
 'Text 94':dict(x=602,y=346,w=94,h=41,size=11,align='ctr'),
 'Text 97':dict(x=637,y=406,w=51,h=15,size=11),
 'Text 100':dict(x=637,y=443,w=52,h=15,size=11),
 'Text 103':dict(x=637,y=483,w=52,h=15,size=11),
 'Text 105':dict(x=33,y=433,w=530,h=21,size=16),
 'Text 108':dict(x=87,y=469,w=103,h=18,size=14),
 'Text 112':dict(x=258,y=469,w=119,h=18,size=13),
 'Text 116':dict(x=444,y=469,w=117,h=18,size=13),
 'Text 109':dict(x=85,y=491,w=105,h=15,size=10.5),
 'Text 113':dict(x=259,y=491,w=115,h=15,size=10.5),
 'Text 117':dict(x=443,y=491,w=117,h=15,size=10.5),
 'Text 32':dict(x=180,y=177,w=300,h=17,size=12.5,align='ctr'),
 'Text 83':dict(x=190,y=395,w=220,h=17,size=12.5,align='ctr'),
}
for name,values in changes.items():configure(shapes[name],**values)
# Keep the existing circled-glyph run in its available symbol font.
for name in ['Text 5','Text 10','Text 15','Text 20']:
    for font in shapes[name].findall('.//a:latin',NS):font.set('typeface','DejaVu Sans')
# A source padlock icon's white bitmap previously covered its lab title. Keep
# each native icon and aspect ratio, moving it within its original column.
for pic in root.findall('.//p:pic',NS):
    name=pic.find('p:nvPicPr/p:cNvPr',NS).get('name')
    if name in ['图片 151','图片 153','图片 155']:
        transform=pic.find('p:spPr/a:xfrm',NS)
        off,ext=transform.find('a:off',NS),transform.find('a:ext',NS)
        w,h=int(ext.get('cx')),int(ext.get('cy'))
        newh=28.5
        ext.set('cx',pt(newh*w/h));ext.set('cy',pt(newh));off.set('y',pt(333))
assert before==original_text(root),'Author wording must remain unchanged'
raw['ppt/slides/slide1.xml']=E.tostring(root,encoding='utf-8',xml_declaration=True)
with ZipFile(DEST,'w',ZIP_DEFLATED) as archive:
    for name,data in raw.items():archive.writestr(name,data)
assert sha(SOURCE)==original_sha
print(json.dumps(dict(source_sha256=original_sha,derived_pptx=str(DEST),
                     derived_sha256=sha(DEST),author_text_identical=True,
                     changed_text_boxes=list(changes),icons_preserved=True),indent=2))
env=os.environ.copy();local=Path('/liziqing/yukai/.local/opt')
env['PATH']=':'.join(str(local/x) for x in ['libreoffice-26.2.5/opt/libreoffice26.2/program','poppler/usr/bin','fontconfig/usr/bin'])+':'+env['PATH']
env['LD_LIBRARY_PATH']=':'.join(str(local/x) for x in ['lo-deps/usr/lib/x86_64-linux-gnu','poppler/usr/lib/x86_64-linux-gnu','fontconfig/usr/lib/x86_64-linux-gnu'])
env['FONTCONFIG_FILE']=str(local/'fontconfig/etc/fonts/fonts.conf');env['FONTCONFIG_PATH']=str(local/'fontconfig/etc/fonts')
subprocess.run(['soffice',f'-env:UserInstallation={(WORK/"repair_profile").as_uri()}',
                '--headless','--convert-to','pdf:impress_pdf_Export','--outdir',str(WORK),str(DEST)],
                env=env,check=True,timeout=90)
import fitz
from PIL import Image
doc=fitz.open(DEST.with_suffix('.pdf'));page=doc[0]
pix=page.get_pixmap(matrix=fitz.Matrix(1500/page.rect.width,1500/page.rect.width),alpha=False)
Image.frombytes('RGB',[pix.width,pix.height],pix.samples).save(WORK/'readable-preview.jpg',quality=85)
print('PREVIEW',WORK/'readable-preview.jpg')

# Crop outer whitespace only. All shape/text positions in the authored slide
# remain unchanged in this publication PDF. Raster icons were already present
# in the source; text, borders, and connector geometry remain vectors.
page=doc[0]
bounds=[]
for block in page.get_text('dict')['blocks']:
    bounds.append(fitz.Rect(block['bbox']))
for drawing in page.get_drawings():
    fill=drawing.get('fill')
    if drawing.get('color') is not None or fill is not None and any(c<.99 for c in fill):
        bounds.append(fitz.Rect(drawing['rect']))
content=bounds[0]
for box in bounds[1:]:content |= box
crop=fitz.Rect(content.x0-4,content.y0-4,content.x1+4,content.y1+4)&page.rect
page.set_cropbox(crop)
output=args.output_dir
output.mkdir(parents=True,exist_ok=True)
name='framework_user_20260923_readable_original_labels'
pdf=output/(name+'.pdf')
doc.save(pdf,garbage=4,deflate=True)
doc.close()
import shutil
editable=output/(name+'.pptx')
shutil.copyfile(DEST,editable)
final=fitz.open(pdf);page=final[0]
png=output/(name+'.png')
page.get_pixmap(matrix=fitz.Matrix(1500/page.rect.width,1500/page.rect.width),alpha=False).save(png)
pix=page.get_pixmap(matrix=fitz.Matrix(1000/page.rect.width,1000/page.rect.width),alpha=False)
jpeg=WORK/'readable-final-1000.jpg'
Image.frombytes('RGB',[pix.width,pix.height],pix.samples).save(jpeg,quality=78)
receipt=dict(source=str(SOURCE),source_sha256=original_sha,source_unchanged=sha(SOURCE)==original_sha,
    derived_editable_pptx=str(editable),derived_pptx_sha256=sha(editable),
    vector_pdf=str(pdf),vector_pdf_sha256=sha(pdf),png_preview=str(png),small_preview=str(jpeg),
    vector_path_count=len(page.get_drawings()),embedded_images=len(page.get_images()),
    crop_box_points=list(crop),page_points=list(page.rect),fonts=[list(x) for x in page.get_fonts()],
    source_text_identical=True,original_connectors_colors_icons_preserved=True,
    changes=['explicit render-available Carlito/DejaVu fonts','text box bounds and sizes',
             'three padlocks placed below lab headings','outside-margin crop'],
    original_source_render='/tmp/ai4ai4cell-framework-padm9cao/original/slide-1.png',
    pending_wording=['Federated in title','Laboratory 10','federated learning in local-data footer',
                     'Aggregated diagnostic guide: original grammatical form retained'],
    authored_diagram_note='No new linking arrow was added between outer and inner panels.',
    final_visual_review_required=True)
final.close()
(output/(name+'.provenance.json')).write_text(json.dumps(receipt,indent=2)+'\n')
assert sha(SOURCE)==original_sha
print(json.dumps(receipt,indent=2))
