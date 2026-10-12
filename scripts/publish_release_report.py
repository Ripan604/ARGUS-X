"""Create the local review PDF from the dated source documents (no upload)."""
from __future__ import annotations
from pathlib import Path
import argparse
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, CondPageBreak, Preformatted, KeepTogether, Flowable, Image

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',default='output/pdf/ARGUS_Release_Readiness.pdf')
parser.add_argument('--documents',nargs='+')
parser.add_argument('--final-disclosure',action='store_true')
parser.add_argument('--probe-v2',action='store_true')
parser.add_argument('--measured-data',action='store_true')
args=parser.parse_args()
OUTPUT=ROOT/args.output
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
for name,file in [('Body','calibri.ttf'),('Body-Bold','calibrib.ttf'),('Body-Italic','calibrii.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Body-Bold',italic='Body-Italic',boldItalic='Body-Bold')
NAVY=colors.HexColor('#142B3B');TEAL=colors.HexColor('#087F8C');INK=colors.HexColor('#243847');MUTED=colors.HexColor('#586D7C')
WIDTH=A4[0]-104
styles={
    'body':ParagraphStyle('body',fontName='Body',fontSize=10.3,leading=14.1,textColor=INK,spaceAfter=8,allowWidows=False,allowOrphans=False),
    'title':ParagraphStyle('title',fontName='Body-Bold',fontSize=23,leading=28,textColor=NAVY,spaceAfter=15),
    'h2':ParagraphStyle('h2',fontName='Body-Bold',fontSize=14,leading=18,textColor=TEAL,spaceBefore=12,spaceAfter=8,keepWithNext=True),
    'small':ParagraphStyle('small',fontName='Body',fontSize=8.5,leading=11.5,textColor=MUTED,spaceAfter=7),
    'cell':ParagraphStyle('cell',fontName='Body',fontSize=8.5,leading=11.2,textColor=INK),
    'head':ParagraphStyle('head',fontName='Body-Bold',fontSize=8.8,leading=11.8,textColor=colors.white),
    'code':ParagraphStyle('code',fontName='Courier',fontSize=8,leading=11,textColor=NAVY),
}


def markup(text):
    text=text.translate({code:ord('-') for code in (0x2010,0x2011,0x2012,0x2013,0x2014,0x2212)})
    text=escape(text)
    text=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<a href="\2" color="#087F8C">\1</a>',text)
    # Relative repository links are useful in Markdown; print their readable
    # labels in the standalone PDF instead of exposing raw Markdown syntax.
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'`([^`]+)`',r'<font name="Courier" size="9">\1</font>',text)
    return text


def paragraph(text,style='body'):
    return Paragraph(markup(text),styles[style])


class PatentDrawings(Flowable):
    def __init__(self,kind):
        Flowable.__init__(self);self.kind=kind;self.width=WIDTH;self.height=170
    def draw(self):
        c=self.canv;c.setStrokeColor(NAVY);c.setFillColor(INK)
        if self.kind==4:
            labels=['Controller + experiment hash','ESP32 shared clock / GPIO26','DAC25 + characterized driver',
                    'Panel / exciter / receiver','ADC34 + timestamped frame','Gate + metrology + replan']
            coordinates=[(0,102),(170,102),(340,102),(340,15),(170,15),(0,15)]
            for (x,y),label in zip(coordinates,labels):
                c.setFillColor(colors.HexColor('#EAF5F5'));c.roundRect(x,y,150,53,5,fill=1)
                c.setFillColor(INK);c.setFont('Body-Bold',9)
                words=label.split();line='';lines=[]
                for word in words:
                    if len(line+' '+word)>24:lines.append(line);line=word
                    else:line=(line+' '+word).strip()
                lines.append(line)
                for j,line in enumerate(lines):c.drawCentredString(x+75,y+35-j*12,line)
            c.setStrokeColor(TEAL);c.setLineWidth(1.5)
            for x1,y1,x2,y2 in [(150,128,169,128),(320,128,339,128),(415,102,415,68),
                               (340,41,321,41),(170,41,151,41),(75,68,75,102)]:
                c.line(x1,y1,x2,y2)
            return
        if self.kind==2:
            c.rect(60,15,365,130);points=[(90,45,'S'),(390,50,'R'),(260,120,'z')]
            for x,y,label in points:
                c.circle(x,y,5,fill=1);c.setFont('Body-Bold',11);c.drawString(x+9,y+4,label)
            c.line(90,45,390,50);c.setDash(4,3);c.line(90,45,260,120);c.line(260,120,390,50);c.setDash()
            c.setFont('Body',10);c.drawString(130,22,'Direct reference: |S-R|');c.drawString(146,149,'Diagnostic path: |S-z| + |z-R|')
            return
        labels=(['Posterior + covariance','Diagnostic geometry','Feasible reference bank','Covariance-conditioned rank','Aligned reference recording','Gate, update and verify']
                if self.kind==3 else ['Exciter / panel','Aligned receiver / DAQ','Validated waveform','Location + metrology state','Task-conditioned controller','Guided physical geometry'])
        coordinates=[(0,102),(170,102),(340,102),(340,15),(170,15),(0,15)]
        for (x,y),label in zip(coordinates,labels):
            c.setFillColor(colors.HexColor('#EAF5F5'));c.roundRect(x,y,150,53,5,fill=1)
            c.setFillColor(INK);c.setFont('Body-Bold',9)
            words=label.split();line='';lines=[]
            for word in words:
                if len(line+' '+word)>25:lines.append(line);line=word
                else:line=(line+' '+word).strip()
            lines.append(line)
            for j,line in enumerate(lines):c.drawCentredString(x+75,y+34-j*12,line)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(TEAL);c.setLineWidth(1.5);c.line(x1,y1,x2,y2)
        arrow(150,128,169,128);arrow(320,128,339,128);arrow(415,102,415,68)
        arrow(340,41,321,41);arrow(170,41,151,41);arrow(75,68,75,102)


def md_blocks(content):
    lines=content.splitlines();out=[];i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip(): i+=1;continue
        if line.startswith('```'):
            i+=1;code=[]
            while i<len(lines) and not lines[i].startswith('```'):
                # Wrap long commands only for layout, preserving the source docs.
                raw=lines[i]
                while len(raw)>84:
                    cut=raw.rfind(' ',0,84)
                    if cut<20: cut=84
                    code.append(raw[:cut]);raw='  '+raw[cut:].lstrip()
                code.append(raw);i+=1
            block=Preformatted('\n'.join(code),styles['code'])
            table=Table([[block]],colWidths=[WIDTH])
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EAF5F5')),('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
            out.extend([table,Spacer(1,10)]);i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',x) for x in cells): rows.append(cells)
                i+=1
            count=len(rows[0]); widths=[WIDTH/count]*count
            if count==3: widths=[WIDTH*.26,WIDTH*.43,WIDTH*.31]
            if count==4: widths=[WIDTH*.23,WIDTH*.17,WIDTH*.39,WIDTH*.21]
            data=[[paragraph(x,'head' if j==0 else 'cell') for x in row] for j,row in enumerate(rows)]
            table=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F2F6F8')]),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#D5E1E7'))]))
            out.extend([table,Spacer(1,10)]);continue
        if line.startswith('# '): out.append(paragraph(line[2:],'title'));i+=1;continue
        if line.startswith('## '): out.append(paragraph(line[3:],'h2'));i+=1;continue
        if line.startswith('- '):
            text=line[2:];i+=1
            while i<len(lines) and lines[i].startswith('  '): text+=' '+lines[i].strip();i+=1
            out.append(paragraph('\u2022 '+text));continue
        if re.match(r'^\d+\.\s',line):
            text=line;i+=1
            while i<len(lines) and lines[i].strip() and not re.match(r'^\d+\.\s',lines[i]) and not lines[i].startswith(('#','|','```','- ')):
                text+=' '+lines[i].strip();i+=1
            out.append(paragraph(text));continue
        text=line;i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','- ')):
            text+=' '+lines[i].strip();i+=1
        out.append(paragraph(text))
    return out


def frame(c,doc):
    c.saveState();c.setFillColor(TEAL);c.setFont('Body-Bold',9);c.drawString(52,A4[1]-33,'ARGUS')
    c.setFillColor(MUTED);c.setFont('Body',8);c.drawRightString(A4[0]-52,A4[1]-33,'MEASURED RESEARCH / 9 OCTOBER 2026' if args.measured_data else 'TECHNICAL REVIEW PACKAGE / 7 OCTOBER 2026')
    c.setStrokeColor(colors.HexColor('#D5E1E7'));c.line(52,A4[1]-42,A4[0]-52,A4[1]-42);c.line(52,45,A4[0]-52,45)
    c.drawString(52,30,'Local research evidence / no physical or patent-validity certificate')
    c.drawRightString(A4[0]-52,30,str(doc.page));c.restoreState()


files=args.documents or ['docs/RELEASE_READINESS_REPORT.md','docs/PATENT_REVIEW_PACKAGE.md','docs/SECURITY.md',
       'docs/PUBLICATION_READINESS.md','docs/VALIDATION_PROTOCOL_2026_10_07.md']
story=[paragraph('ARGUS: measured data and reference control' if args.measured_data else 'ARGUS: acquisition v2 and extended evidence' if args.probe_v2 else 'ARGUS: final technical disclosure and evidence' if args.final_disclosure else 'ARGUS: hardened prototype and technical review package','title'),
       paragraph('Licensed measured datasets, held-out evaluations, failure evidence and experimental nuisance-aware reference control.' if args.measured_data else 'Project explanation, clock-referenced apparatus implementation, strong reference-design comparisons and claim-support boundaries.' if args.probe_v2 else 'Implemented reference-selection method, bounded synthetic evidence, draft claim concepts and enabling drawings.' if args.final_disclosure else 'Security fixes, scientific integrity, fresh synthetic evaluation, publication scope and IP support.'),
       Spacer(1,14),paragraph('Read this first','h2'),
       paragraph('Measured tap screening has a useful plate-held-out result. Native ultrasonic localization and cross-panel quality rejection remain inadequate. Healthy-reference transport improves development waveform agreement, but separate confirmation shows worse adaptive localization and missed damage conditions. Zero false alarms does not rescue an insensitive detector. Development and confirmation remain distinct; the user apparatus, field coverage and patent novelty are unvalidated.' if args.measured_data else 'The implemented probe captures during excitation and binds a complete clock-described frame before inference. External timing/transfer validation remains necessary. The expanded study retains comparisons against strong baselines and reports synthetic arrival prediction separately from physical localization. Publication and grant are separate procedures, and no numerical acceptance probability is established.' if args.probe_v2 else 'The optional selector has positive evidence for diagnostic-arrival prediction in a declared scalar simulation. Earlier waveform stress failures remain visible. The final package identifies the implemented technical interaction, claim-support limits and physical-acquisition requirements; novelty, inventorship and filing status remain external questions.' if args.final_disclosure else 'The code controls and reproducibility package have been strengthened and tested. The fresh stress study still contains large errors. This package makes the scope inspectable; it does not replace physical validation or establish novelty, filing status, acceptance or a course grade.'),
       paragraph('Contents','h2')]
for file in files:
    story.append(paragraph((ROOT/file).read_text(encoding='utf-8').splitlines()[0].lstrip('# ')))
story.append(Spacer(1,16))
story.append(paragraph('Source documents and exact commands remain in docs/. Current JSON and JUnit evidence remain in output/release/ and research_results/. The separate manuscript PDF is compiled from paper/main.tex.','small'))
if args.final_disclosure or args.probe_v2:
    story.append(PageBreak());story.append(paragraph('Drawings and physical boundary','title'))
    for kind,caption in [(4 if args.probe_v2 else 1,'Figure 1. Implemented clock-described v2 acquisition and inference interaction; analog timing and transfer require bench measurements.' if args.probe_v2 else 'Figure 1. Control-system blocks; the aligned physical DAQ is a proposed apparatus embodiment requiring measured timing.'),
                         (2,'Figure 2. Direct-reference and bistatic diagnostic geometry on a rectangular panel.'),
                         (3,'Figure 3. Implemented optional reference selection and gated update sequence. Covariance ranking uses all posterior mass.')]:
        story.append(PatentDrawings(kind));story.append(paragraph(caption,'small'))
if args.measured_data:
    story.append(PageBreak());story.append(paragraph('Measured results at their actual scope','title'))
    figures=[('measured_gfrp_scores.png', 'Figure 1. Pointwise audio-tap screening with entire plates held out. Eight clusters support the intervals.'),
             ('measured_impact_errors.png', 'Figure 2. Transient source-position error on nine previously seen records. Dots are retained position errors.'),
             ('measured_ogw_budget.png', 'Figure 3. Conditional location error versus revealed paths. Full-bank references cost 66 paths; curves are not operational detection accuracy.'),
             ('measured_morpho_bad_recall.png', 'Figure 4. Cross-panel BAD-signal rejection fails despite apparently high overall accuracy.')]
    for index,(filename,caption) in enumerate(figures):
        if index==2:story.append(PageBreak())
        path=ROOT/'output/figures'/filename
        figure=Image(str(path));figure.drawHeight=WIDTH*figure.imageHeight/figure.imageWidth;figure.drawWidth=WIDTH
        story.append(KeepTogether([figure,paragraph(caption,'small'),Spacer(1,14)]))
    fundamental=ROOT/'output/figures/reference_conditioned_development.png'
    if fundamental.exists():
        story.append(PageBreak());story.append(paragraph('Reference control: measured development','title'))
        figure=Image(str(fundamental));figure.drawHeight=WIDTH*figure.imageHeight/figure.imageWidth;figure.drawWidth=WIDTH
        story.append(figure)
        story.append(paragraph('Figure 5. Healthy-reference development improves waveform agreement while conditional localization worsens. Only 20 of 66 paths qualify; the horizon is 16. These results reuse previously seen data.','small'))
    confirmation=ROOT/'output/figures/reference_conditioned_confirmation.png'
    if confirmation.exists():
        story.append(CondPageBreak(280));story.append(paragraph('Separate confirmation: negative result','h2'))
        figure=Image(str(confirmation));figure.drawHeight=WIDTH*figure.imageHeight/figure.imageWidth;figure.drawWidth=WIDTH
        story.append(KeepTogether([figure,paragraph('Figure 6. All 29 new banks were verified and scored with frozen parameters. Adaptive transported localization is worse than raw localization. All adaptive variants miss the eight damage conditions; zero false alarms on two unique healthy banks is not successful detection. Correlated calibration and one specimen leave field coverage unestablished.','small')]))
for index,file in enumerate(files):
    story.append(PageBreak() if index==0 else CondPageBreak(240))
    if index: story.append(Spacer(1,16))
    story.extend(md_blocks((ROOT/file).read_text(encoding='utf-8')))
doc=SimpleDocTemplate(str(OUTPUT),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=63,bottomMargin=62,
                      title='ARGUS Release Readiness and Technical Review',author='ARGUS project review')
doc.build(story,onFirstPage=frame,onLaterPages=frame)
print(OUTPUT)
