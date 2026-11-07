"""Build the printable Chinese interview manual from its editable Markdown source."""
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
ROOT=Path(__file__).resolve().parents[1]
doc=Document();sec=doc.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=Inches(.72);sec.bottom_margin=Inches(.7);sec.left_margin=Inches(.8);sec.right_margin=Inches(.8)
for name,size in [('Normal',11),('Title',23),('Subtitle',11),('Heading 1',16),('Heading 2',12)]:
    style=doc.styles[name];style.font.name='Noto Sans CJK SC';style.font.size=Pt(size);style.font.color.rgb=RGBColor(0,0,0)
    style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Noto Sans CJK SC')
    style.paragraph_format.space_after=Pt(7 if name=='Normal' else 9)
    style.paragraph_format.line_spacing=1.17
    if name.startswith('Heading'):style.paragraph_format.space_before=Pt(11)
normal=doc.styles['Normal'];normal.paragraph_format.widow_control=True
for line in (ROOT/'docs/interview_handbook.md').read_text().splitlines():
    if not line.strip():continue
    if line.startswith('# '):doc.add_paragraph(line[2:],'Title');doc.add_paragraph('公开随机实验分析  方法解释  实际结果  面试问答','Subtitle')
    elif line.startswith('## '):doc.add_paragraph(line[3:],'Heading 1')
    elif line.startswith('### '):doc.add_paragraph(line[4:],'Heading 2')
    else:doc.add_paragraph(line)
# Page numbering helps a long manual; no ornamental title lines.
p=sec.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run();r.font.size=Pt(9)
f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');r._r.addnext(f)
doc.core_properties.title='邮件营销实验项目面试手册'
doc.core_properties.subject='Hillstrom实验分析与增量策略评估'
doc.core_properties.author=''
for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
for para in doc.paragraphs:
    for border in list(para._p.iter(qn('w:pBdr'))):border.getparent().remove(border)
doc.save(ROOT/'docs/interview_handbook.docx')
print(ROOT/'docs/interview_handbook.docx')
