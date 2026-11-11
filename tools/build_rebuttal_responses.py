"""Build a readable response PDF from the three author-reviewable Markdown replies."""
from pathlib import Path
import argparse
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

PAPER = Path(__file__).resolve().parents[1]
SOURCE = PAPER / 'provenance/rebuttal_20261109'
DESTINATION = PAPER / 'output/pdf/BioCoLoop_reviewer_responses_20261109.pdf'


def markup(text):
    text = escape(text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                  lambda m: '<link href="' + m[2] + '">' + m[1] + '</link>', text)
    return re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewers', nargs='+', choices=('FBhK', 'AfJB', 'cR5g'),
                        default=['FBhK', 'AfJB', 'cR5g'])
    parser.add_argument('--output', type=Path, default=DESTINATION)
    parser.add_argument('--revision-date', default='9 November 2026')
    args = parser.parse_args()
    fonts = Path('/usr/share/fonts/truetype/liberation')
    if (fonts / 'LiberationSerif-Regular.ttf').exists():
        files = {suffix: fonts / f'LiberationSerif-{suffix}.ttf'
                 for suffix in ('Regular', 'Bold', 'Italic', 'BoldItalic')}
    else:
        from matplotlib import get_data_path
        fonts = Path(get_data_path()) / 'fonts/ttf'
        files = {suffix: fonts / ('DejaVuSerif.ttf' if suffix == 'Regular'
                                  else f'DejaVuSerif-{suffix}.ttf')
                 for suffix in ('Regular', 'Bold', 'Italic', 'BoldItalic')}
    for name, suffix in [('ReplySerif', 'Regular'), ('ReplySerif-Bold', 'Bold'),
                         ('ReplySerif-Italic', 'Italic'), ('ReplySerif-BoldItalic', 'BoldItalic')]:
        pdfmetrics.registerFont(TTFont(name, str(files[suffix])))
    pdfmetrics.registerFontFamily('ReplySerif', normal='ReplySerif', bold='ReplySerif-Bold',
        italic='ReplySerif-Italic', boldItalic='ReplySerif-BoldItalic')
    styles = dict(body=ParagraphStyle('Body', fontName='ReplySerif', fontSize=10.5,
            leading=12.25, spaceAfter=3, alignment=TA_LEFT),
        heading=ParagraphStyle('Heading', fontName='ReplySerif-Bold', fontSize=11.5,
            leading=14, spaceBefore=8, spaceAfter=5, keepWithNext=True),
        title=ParagraphStyle('Title', fontName='ReplySerif-Bold', fontSize=17,
            leading=20, spaceAfter=12, keepWithNext=True),
        note=ParagraphStyle('Note', fontName='ReplySerif-Italic', fontSize=9,
            leading=12, textColor=colors.HexColor('#555555'), spaceAfter=10))
    story = []
    for index, reviewer in enumerate(args.reviewers):
        if index:
            story.append(PageBreak())
        text = (SOURCE / f'RESPONSE_{reviewer}.md').read_text()
        for para in text.strip().split('\n\n'):
            if para.startswith('# '):
                story.append(Paragraph(markup(para[2:]), styles['title']))
                story.append(Paragraph('BioCoLoop, submission 5046 | Revision dated ' + escape(args.revision_date) + '.',
                    styles['note']))
            elif para.startswith('## '):
                story.append(Paragraph(markup(para[3:]), styles['heading']))
            else:
                story.append(Paragraph(markup(para.replace('\n', ' ')), styles['body']))
    def footer(canvas, doc):
        canvas.setFont('ReplySerif', 9)
        canvas.setFillColor(colors.HexColor('#555555'))
        canvas.drawString(44, 27, 'BioCoLoop - reviewer responses')
        canvas.drawRightString(A4[0] - 44, 27, str(doc.page))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(args.output), pagesize=A4,
        rightMargin=44, leftMargin=44, topMargin=42, bottomMargin=42,
        title='BioCoLoop - Responses to Reviewers ' + ', '.join(args.reviewers), author='')
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.output)


if __name__ == '__main__':
    main()
