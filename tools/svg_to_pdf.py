# Render an SVG figure to PDF (pt = 0.75 px) or PNG (2.5x) with librsvg/cairo: python3 tools/svg_to_pdf.py in.svg out.pdf
import sys, ctypes as C
rsvg = C.CDLL('librsvg-2.so.2'); cairo = C.CDLL('libcairo.so.2')
class Rect(C.Structure): _fields_=[('x',C.c_double),('y',C.c_double),('width',C.c_double),('height',C.c_double)]
rsvg.rsvg_handle_new_from_file.restype=C.c_void_p
rsvg.rsvg_handle_new_from_file.argtypes=[C.c_char_p,C.c_void_p]
rsvg.rsvg_handle_get_intrinsic_size_in_pixels.argtypes=[C.c_void_p,C.POINTER(C.c_double),C.POINTER(C.c_double)]
rsvg.rsvg_handle_render_document.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(Rect),C.c_void_p]
for f in ['cairo_pdf_surface_create','cairo_image_surface_create','cairo_create']: getattr(cairo,f).restype=C.c_void_p
cairo.cairo_pdf_surface_create.argtypes=[C.c_char_p,C.c_double,C.c_double]
cairo.cairo_image_surface_create.argtypes=[C.c_int,C.c_int,C.c_int]
cairo.cairo_create.argtypes=[C.c_void_p]
for f in ['cairo_surface_finish','cairo_destroy','cairo_paint']: getattr(cairo,f).argtypes=[C.c_void_p]
cairo.cairo_set_source_rgb.argtypes=[C.c_void_p,C.c_double,C.c_double,C.c_double]
cairo.cairo_surface_write_to_png.argtypes=[C.c_void_p,C.c_char_p]
src,out=sys.argv[1],sys.argv[2]
h=rsvg.rsvg_handle_new_from_file(src.encode(),None); assert h
w=C.c_double(); hh=C.c_double(); rsvg.rsvg_handle_get_intrinsic_size_in_pixels(h,C.byref(w),C.byref(hh))
pdf=out.endswith('.pdf'); s=0.75 if pdf else 2.5
surf=cairo.cairo_pdf_surface_create(out.encode(),w.value*s,hh.value*s) if pdf else cairo.cairo_image_surface_create(0,int(w.value*s),int(hh.value*s))
ctx=cairo.cairo_create(surf)
if not pdf:
    cairo.cairo_set_source_rgb(ctx,1,1,1); cairo.cairo_paint(ctx)
r=Rect(0,0,w.value*s,hh.value*s)
assert rsvg.rsvg_handle_render_document(h,ctx,C.byref(r),None)
cairo.cairo_destroy(ctx)
if not pdf:
    cairo.cairo_surface_write_to_png(surf,out.encode())
cairo.cairo_surface_finish(surf)
print(out,w.value,hh.value)
