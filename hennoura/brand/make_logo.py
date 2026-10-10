"""Generate Hennoura logo SVGs with all text converted to outlined paths (no font dependency)."""
import uharfbuzz as hb, cairosvg, io
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
G="/usr/share/fonts/truetype/sand-box/google/"
AR=G+"El Messiri/ElMessiri-VariableFont_wght.ttf"
LA=G+"Cormorant Garamond/CormorantGaramond-VariableFont_wght.ttf"

def inst(path,w):
    f=TTFont(path); f=instancer.instantiateVariableFont(f,{"wght":w}); b=io.BytesIO(); f.save(b); return b.getvalue()

def shape_path(fontbytes,text,size,x0,ybase,align="center",tracking=0,direction=None):
    face=hb.Face(fontbytes); font=hb.Font(face); upem=face.upem
    buf=hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    if direction: buf.direction=direction
    hb.shape(font,buf,{"kern":True,"liga":True})
    tt=TTFont(io.BytesIO(fontbytes)); gs=tt.getGlyphSet(); order=tt.getGlyphOrder()
    s=size/upem; tr=tracking*upem/size if size else 0
    total=sum(p.x_advance for p in buf.glyph_positions)+tr*(len(buf.glyph_infos)-1)
    if align=="center": start=x0-total*s/2
    elif align=="right": start=x0-total*s
    else: start=x0
    pen=SVGPathPen(gs); cx=0
    for i,(info,pos) in enumerate(zip(buf.glyph_infos,buf.glyph_positions)):
        g=order[info.codepoint]
        t=TransformPen(pen,(s,0,0,-s,start+(cx+pos.x_offset)*s,ybase-pos.y_offset*s))
        gs[g].draw(t); cx+=pos.x_advance+tr
    return pen.getCommands(), total*s

AR600=inst(AR,600); LA500=inst(LA,500)

def yaz(cx,cy,h,stroke,color):
    # Tifinagh yaz ⵣ drawn geometrically: stem + two mirrored arcs
    w=h*0.62; t=h/2
    return (f'<g fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round">'
            f'<path d="M{cx},{cy-t} V{cy+t}"/>'
            f'<path d="M{cx-w/2},{cy-t} Q{cx-w/2},{cy-h*0.12} {cx},{cy-h*0.12} Q{cx+w/2},{cy-h*0.12} {cx+w/2},{cy-t}"/>'
            f'<path d="M{cx-w/2},{cy+t} Q{cx-w/2},{cy+h*0.12} {cx},{cy+h*0.12} Q{cx+w/2},{cy+h*0.12} {cx+w/2},{cy+t}"/></g>')

def arch(cx,top,w,h,stroke,color):
    # Moroccan horseshoe-ish arch frame around the mark
    r=w/2
    return (f'<path d="M{cx-r},{top+h} V{top+r} A{r},{r} 0 0 1 {cx+r},{top+r} V{top+h}" '
            f'fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linejoin="round"/>')

def build(main,accent,sub,bg=None,W=600,H=460):
    ar,arw=shape_path(AR600,"حنّورة",150,W/2,300,"center")
    la,law=shape_path(LA500,"HENNOURA",38,W/2,372,"center",tracking=14)
    tag,_=shape_path(LA500,"MAROC · NATURAL HAIR RITUAL",15,W/2,410,"center",tracking=4)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">',
           '<title id="t">Hennoura · حنّورة</title>']
    if bg: parts.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')
    parts.append(arch(W/2,22,84,120,3,accent))
    parts.append(yaz(W/2,92,62,5,accent))
    parts.append(f'<path d="{ar}" fill="{main}"/>')
    parts.append(f'<path d="{la}" fill="{main}"/>')
    parts.append(f'<line x1="{W/2-120}" y1="390" x2="{W/2+120}" y2="390" stroke="{accent}" stroke-width="1"/>')
    parts.append(f'<path d="{tag}" fill="{sub}"/>')
    parts.append('</svg>')
    return "\n".join(parts)

def mark(color,bg=None,S=512):
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">']
    if bg: p.append(f'<rect width="{S}" height="{S}" rx="{S*0.22}" fill="{bg}"/>')
    p.append(arch(S/2,S*0.12,S*0.56,S*0.76,S*0.025,color)); p.append(yaz(S/2,S*0.56,S*0.4,S*0.04,color)); p.append('</svg>')
    return "\n".join(p)

GREEN="#2F4A3A"; GOLD="#B08D57"; SAND="#F4EBDD"; TERRA="#A4532F"; INK="#1E2A22"
out="/workspace/henna-sidr/store/brand/"
open(out+"logo.svg","w").write(build(GREEN,GOLD,TERRA))
open(out+"logo-dark.svg","w").write(build(SAND,GOLD,"#D9C7A8"))
open(out+"mark.svg","w").write(mark(GOLD))
open(out+"favicon.svg","w").write(mark(SAND,GREEN))
for name,bg in [("logo",SAND),("logo-dark",GREEN)]:
    svg=open(out+name+".svg").read().replace('role="img"',f'role="img" style="background:{bg}"',1)
    svg=svg.replace('<title id="t">Hennoura · حنّورة</title>',f'<title id="t">Hennoura</title><rect width="600" height="460" fill="{bg}"/>',1)
    cairosvg.svg2png(bytestring=svg.encode(),write_to=out+name+"-preview.png",output_width=1200)
cairosvg.svg2png(bytestring=open(out+"favicon.svg").read().encode(),write_to=out+"favicon-512.png",output_width=512)
print("done")
