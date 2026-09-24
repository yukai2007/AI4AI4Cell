// Editable counterpart of assets/paradigm_comparison.pdf.
// Recreates the same labels and semantic geometry with native PowerPoint objects.
// Does not modify the active manuscript artwork. Run: node draw_figure_1.js [outDir]
const fs = require('fs');
const path = require('path');
const PptxGenJS = require('pptxgenjs');
const out = path.resolve(process.argv[2] || __dirname);
fs.mkdirSync(out, { recursive: true });
const pptx = new PptxGenJS();
pptx.defineLayout({ name: 'PARADIGMS', width: 11, height: 6.1 });
pptx.layout = 'PARADIGMS';
pptx.author = '';
pptx.subject = 'Editable Figure 1; native shapes, text and arrows';
pptx.title = 'BioCoLoop: research paradigms';
pptx.company = '';
pptx.lang = 'en-US';
pptx.theme = { headFontFace: 'DejaVu Sans', bodyFontFace: 'DejaVu Sans', lang: 'en-US' };
const slide = pptx.addSlide();
slide.background = { color: 'FFFFFF' };
const c = { ink: '172B3A', secondary: '536475', data: '238B7B', dataFill: 'E7F5F2',
  model: '356FA3', modelFill: 'E8F1F8', harness: '76539A', harnessFill: 'F1EAF7',
  gate: 'C76A28', gateFill: 'FBEDE3', ghost: '8B98A3', ghostFill: 'F4F6F7', divider: 'D9E0E5' };
const X = x => x * 11 / 12;
const Y = y => (6.65 - y) * 6.1 / 6.65;
const W = w => w * 11 / 12;
const H = h => h * 6.1 / 6.65;
const meta = { active_source: 'assets/paradigm_comparison.pdf',
  reference_generator: 'tools/draw_paradigm_comparison.py', canvas_inches: [11, 6.1],
  native_only: true, objects: [] };

function text(id, value, x, y, w, h, size = 7, color = c.ink, bold = false, align = 'center', rotation = 0) {
  // Rectangles intentionally contain text; their overlap is the card design.
  slide.addText(value, { x: X(x), y: Y(y + h), w: W(w), h: H(h), fontFace: 'DejaVu Sans',
    fontSize: size * 2, color, bold, align, valign: 'mid', margin: 0,
    paraSpaceAfterPt: 0, lineSpacingMultiple: 1.0, rotate: rotation,
    objectName: id, isTextBox: true });
  meta.objects.push({ id, text: value, x, y, w, h });
}
function box(id, x, y, w, h, value, role, active = true, size = 7.2) {
  const edge = active ? c[role] : c.ghost;
  const fill = active ? c[role + 'Fill'] : c.ghostFill;
  slide.addShape(pptx.ShapeType.roundRect, { x: X(x), y: Y(y + h), w: W(w), h: H(h),
    radius: 0.06, rectRadius: 0.06, fill: { color: fill },
    line: { color: edge, width: 1.3, ...(active ? {} : { dashType: 'dash' }) }, objectName: id });
  text(id + '_text', value, x + .04, y + .025, w - .08, h - .05, size, edge, true);
}
function line(id, p, q, color, endArrow = false, both = false, width = 1.3) {
  const ax = X(p[0]), ay = Y(p[1]), bx = X(q[0]), by = Y(q[1]);
  const dx = bx - ax, dy = by - ay;
  const reverse = Math.abs(dx) < 1e-8 ? dy < 0 : dx < 0;
  slide.addShape(pptx.ShapeType.line, { x: Math.min(ax, bx), y: Math.min(ay, by),
    w: Math.abs(dx), h: Math.abs(dy), flipV: dx * dy < 0,
    line: { color, width, beginArrowType: both || (endArrow && reverse) ? 'triangle' : 'none',
      endArrowType: both || (endArrow && !reverse) ? 'triangle' : 'none' }, objectName: id });
}
function route(id, points, color) {
  for (let i = 0; i < points.length - 1; i++) line(id + '_' + i, points[i], points[i+1], color, i === points.length - 2);
}
function blueprint(x, mode, id) {
  box(id + '_research', x + .55, 5.03, 2.65, .67, 'Research harness\nPropose · remember', 'harness', mode !== 'collab');
  box(id + '_model', x + .68, 4.00, 2.39, .65, 'Model design\n+ predictor', 'model');
  box(id + '_fitting', x + .68, 2.88, 2.39, .65,
    mode === 'central' ? 'Local fitting\n+ evaluation' : 'Aggregate updates\n+ scores',
    mode === 'central' ? 'model' : 'gate', true, 7.0);
  const labs = [x + .14, x + 1.44, x + 2.74];
  if (mode === 'central') {
    box(id + '_data', x + 1.12, 1.47, 1.51, .66, 'Accessible\nlocal data', 'data', true, 7.0);
  } else {
    labs.forEach((lx, i) => box(id + '_lab_' + i, lx, 1.47, .91, .66, ['Lab 1', 'Lab 2', 'Lab K'][i] + '\nData', 'data', true, 7.0));
    text(id + '_ellipsis', '...', x + 2.37, 1.64, .32, .32, 7, c.data);
  }
  line(id + '_model_down', [x + 1.18, 3.99], [x + 1.18, 3.55], c.model, true);
  line(id + '_model_up', [x + 2.57, 3.54], [x + 2.57, 3.98], mode === 'central' ? c.model : c.gate, true);
  if (mode === 'central') line(id + '_data_up', [x + 1.875, 2.15], [x + 1.875, 2.86], c.data, true);
  else {
    labs.forEach((lx, i) => line(id + '_local_update_' + i, [lx + .455, 2.15], [[x + 1.02, x + 1.88, x + 2.72][i], 2.86], c.model, true, true));
    text(id + '_local_note', 'Train locally; share updates', x + .03, 1.015, 3.70, .33, 6.7, c.secondary);
  }
  if (mode !== 'collab') {
    line(id + '_proposal', [x + 1.34, 5.02], [x + 1.34, 4.67], c.harness, true);
    route(id + '_feedback', [[x + 3.08, 3.20], [x + 3.44, 3.20], [x + 3.44, 5.36], [x + 3.21, 5.36]], c.gate);
    // Use a narrow text area and native vertical text to avoid rotated-box overflow.
    slide.addText(mode === 'central' ? 'Results' : 'Evidence', {
      x: X(x + 3.52), y: Y(5.13), w: W(.30), h: H(1.72),
      fontFace: 'DejaVu Sans', fontSize: 13.4, color: c.gate, align: 'center', valign: 'mid',
      margin: 0, vert: 'vert270', objectName: id + '_feedback_label' });
  }
}

const panels = [[.10, '(a) Centralized bio-agent', 'Centralized access', 'central'],
  [4.10, '(b) Collaborative training', 'Fixed design', 'collab'],
  [8.10, '(c) BioCoLoop', 'Model + design learning', 'ours']];
panels.forEach(([x, title, subtitle, mode], i) => {
  text('title_' + i, title, x - .015, 6.14, 3.78, .38, 7.8, c.ink, true);
  text('subtitle_' + i, subtitle, x + .02, 5.865, 3.71, .31, 6.8, c.secondary);
  blueprint(x, mode, 'panel_' + i);
});
[4, 8].forEach((x, i) => line('divider_' + i, [x, .98], [x, 6.47], c.divider, false, false, 1));
[[1.05, 'data', 'Data'], [3.1, 'model', 'Predictor'], [5.8, 'harness', 'Research loop'], [9.1, 'gate', 'Aggregation']].forEach(([x, role, label], i) => {
  slide.addShape(pptx.ShapeType.roundRect, { x: X(x), y: Y(.65), w: W(.26), h: H(.22),
    radius: .025, rectRadius: .025, fill: { color: c[role + 'Fill'] }, line: { color: c[role], width: 1.2 }, objectName: 'legend_chip_' + i });
  text('legend_' + i, label, x + .38, .385, 2.02, .31, 6.7, c.ink, false, 'left');
});
text('footer', 'Dashed gray: inactive harness. K denotes laboratories.', 1.0, .015, 10.0, .29, 6.5, c.secondary);
slide.addNotes('Editable counterpart of manuscript Figure 1. Native PowerPoint text, shapes and arrows. Layout preserves the three active source paradigms. Editing this deck does not update the paper until it is exported and explicitly installed.');
fs.writeFileSync(path.join(out, 'Figure_1_research_paradigms.layout.json'), JSON.stringify(meta, null, 2) + '\n');
pptx.writeFile({ fileName: path.join(out, 'Figure_1_research_paradigms.pptx') });
