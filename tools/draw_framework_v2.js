// BioCoLoop architecture, rebuilt as editable PowerPoint-native vector shapes.
// Node invocation: node tools/draw_framework_v2.js /absolute/work-directory
const fs = require('fs');
const path = require('path');
let PptxGenJS;
try { PptxGenJS = require('pptxgenjs'); }
catch (_) { PptxGenJS = require(path.join(__dirname, '../tmp/figure_v2_tools/node_modules/pptxgenjs')); }

const outDir = path.resolve(process.argv[2] || path.join(__dirname, '../tmp/framework_v2'));
fs.mkdirSync(outDir, { recursive: true });
const pptx = new PptxGenJS();
pptx.defineLayout({ name: 'FRAMEWORK_4_3', width: 12, height: 9 });
pptx.layout = 'FRAMEWORK_4_3';
pptx.author = '';
pptx.subject = 'Editable architecture for collaborative biological model improvement';
pptx.title = 'BioCoLoop framework';
pptx.company = '';
pptx.lang = 'en-US';
pptx.theme = { headFontFace: 'Carlito', bodyFontFace: 'Carlito', lang: 'en-US' };

const c = {
  ink: '223247', muted: '526171', rule: 'D3DDE5', white: 'FFFFFF', neutral: 'F8FAFC',
  data: '2D7F60', dataFill: 'E9F4ED', model: '276CA6', modelFill: 'EAF2FB',
  research: '76529C', researchFill: 'F4EFFA', gate: 'AE7319', gateFill: 'FFF4DC',
};
const slide = pptx.addSlide();
slide.background = { color: c.white };
const metadata = { layout_inches: [12, 9], font: 'Carlito', native_only: true,
  color_roles: { data: c.data, predictor: c.model, research: c.research, aggregation: c.gate },
  text_boxes: [], nodes: [], edges: [] };

function rect(id, x, y, w, h, fill, border, radius = 0.09, width = 1.2) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h, rectRadius: radius,
    fill: { color: fill }, line: { color: border, width }, radius });
  metadata.nodes.push({ id, x, y, w, h });
}
function text(id, value, x, y, w, h, size = 16, color = c.ink, bold = false, align = 'left') {
  slide.addText(value, { x, y, w, h, fontFace: 'Carlito', fontSize: size, color, bold,
    align, valign: 'mid', margin: 0, breakLine: false, paraSpaceAfterPt: 0,
    lineSpacingMultiple: 1.0, isTextBox: true });
  metadata.text_boxes.push({ id, text: value, x, y, w, h, font_size: size });
}
function line(id, x1, y1, x2, y2, color, arrow = true, width = 1.8) {
  if (Math.abs(x1 - x2) > 1e-8 && Math.abs(y1 - y2) > 1e-8) {
    throw new Error('Only deliberately routed orthogonal connectors are supported');
  }
  const reverse = x2 < x1 || y2 < y1;
  slide.addShape(pptx.ShapeType.line, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    line: { color, width, beginArrowType: arrow && reverse ? 'triangle' : 'none',
      endArrowType: arrow && !reverse ? 'triangle' : 'none' },
  });
  metadata.edges.push({ id, x1, y1, x2, y2, arrow, color });
}
function pathLine(id, points, color, width = 1.8) {
  points.slice(1).forEach((point, i) => line(id + '_' + i,
    points[i][0], points[i][1], point[0], point[1], color, i === points.length - 2, width));
}

// Structural frames intentionally enclose the editable cards and connectors.
rect('outer_frame', 0.25, 1.08, 11.5, 2.19, c.researchFill, 'D7C5E9', 0.15, 1.35);
rect('inner_frame', 0.25, 3.90, 9.23, 3.35, c.neutral, c.rule, 0.15, 1.35);
rect('outputs_frame', 9.70, 4.30, 2.05, 2.95, c.white, c.rule, 0.13, 1.35);

text('title', 'BioCoLoop', 0.32, 0.14, 2.26, 0.43, 26, c.ink, true);
text('subtitle', 'Collaborative biological model improvement', 2.68, 0.20, 8.99, 0.34, 19.4, c.ink);
[
  [0.57, 'Local data', c.data, c.dataFill],
  [3.02, 'Predictors', c.model, c.modelFill],
  [5.73, 'Research loop', c.research, c.researchFill],
  [8.98, 'Aggregation', c.gate, c.gateFill],
].forEach(([x, label, color, fill], i) => {
  rect('legend_chip_' + i, x, 0.75, 0.20, 0.20, fill, color, 0.02, 1.1);
  text('legend_' + i, label, x + 0.31, 0.71, 2.19, 0.28, 15.0, c.ink);
});
text('outer_label', 'OUTER RESEARCH LOOP', 0.51, 1.19, 4.8, 0.27, 17.2, c.research, true);
text('controller_label', 'Research language model: fixed weights', 6.77, 1.19, 4.60, 0.27, 14.1, c.muted, false, 'right');

const cards = [
  { x: 0.50, title: 'Propose', body: 'Hypothesis +\ndesign identifier' },
  { x: 3.26, title: 'Instantiate', body: 'Resolve full recipe;\nbuild executable candidate' },
  { x: 6.02, title: 'Train + evaluate', body: 'Fit locally; return\nscores + diagnostics' },
  { x: 8.78, title: 'Retain / revise', body: 'Higher mean dev score;\ntie → lower mean loss' },
];
cards.forEach((card, i) => {
  rect('research_card_' + i, card.x, 1.92, 2.35, 1.20, c.white, c.research, 0.10, 1.25);
  slide.addShape(pptx.ShapeType.ellipse, { x: card.x + 0.13, y: 2.055, w: 0.29, h: 0.29,
    fill: { color: c.researchFill }, line: { color: c.research, width: 1.0 } });
  text('research_number_' + i, String(i + 1), card.x + 0.13, 2.055, 0.29, 0.29, 13.2, c.research, true, 'center');
  text('research_title_' + i, card.title, card.x + 0.49, 2.01, 1.77, 0.36, 17.1, c.ink, true);
  text('research_body_' + i, card.body, card.x + 0.13, 2.48, 2.09, 0.49, 15.2, c.muted, false, 'center');
  if (i < 3) line('research_sequence_' + i, card.x + 2.35, 2.53, cards[i + 1].x, 2.53, c.research);
});
// History returns above the cards rather than crossing execution traffic.
pathLine('history_feedback', [[9.95, 1.92], [9.95, 1.77], [1.675, 1.77], [1.675, 1.92]], c.research, 1.5);
text('history_feedback_label', 'Evidence cards + previous trials', 3.81, 1.48, 4.35, 0.24, 14.0, c.research, false, 'center');

text('inner_label', 'INNER COLLABORATIVE TRAINING', 0.50, 4.025, 6.6, 0.28, 17.0, c.ink, true);
rect('coordinator', 0.50, 4.43, 8.72, 0.72, c.gateFill, c.gate, 0.11, 1.4);
text('coordinator_title', 'Shared coordinator: run, aggregate, select', 0.70, 4.50, 8.30, 0.29, 17.3, c.ink, true, 'center');
text('coordinator_subtitle', 'Broadcast parameters; aggregate local states + development scores', 0.70, 4.84, 8.30, 0.23, 14.2, c.muted, false, 'center');

// These three distinct channels are separated in x; no forward/backward crossings.
line('candidate_design', 7.195, 3.12, 7.195, 4.43, c.research, true, 2.0);
text('candidate_label', 'Candidate recipe (full config)', 5.10, 3.50, 1.90, 0.29, 14.2, c.research, false, 'right');
pathLine('aggregate_evidence', [[8.90, 4.43], [8.90, 3.54], [9.43, 3.54], [9.43, 3.12]], c.gate, 2.0);
text('evidence_label', 'Dev evidence:\nscore + loss + diagnostics', 7.46, 3.40, 1.27, 0.43, 13.7, c.gate, false, 'center');
line('retained_outputs', 10.65, 3.12, 10.65, 4.30, c.research, true, 1.8);
text('selected_label', 'Selected', 10.81, 3.62, 0.88, 0.25, 13.6, c.research);

const laboratories = [
  { x: 0.50, label: 'Lab 1', scenario: 'Scenario A' },
  { x: 3.49, label: 'Lab 2', scenario: 'Scenario B' },
  { x: 6.48, label: 'Lab K', scenario: 'Scenario K' },
];
laboratories.forEach((lab, i) => {
  rect('laboratory_' + i, lab.x, 5.84, 2.74, 1.03, c.white, c.rule, 0.08, 1.1);
  text('laboratory_name_' + i, lab.label, lab.x + 0.13, 5.92, 0.88, 0.29, 16.2, c.ink, true);
  text('laboratory_scenario_' + i, lab.scenario, lab.x + 1.09, 5.94, 1.51, 0.24, 14.0, c.muted, false, 'right');
  rect('local_data_' + i, lab.x + 0.12, 6.32, 1.10, 0.42, c.dataFill, c.data, 0.05, 1.0);
  rect('local_model_' + i, lab.x + 1.53, 6.32, 1.10, 0.42, c.modelFill, c.model, 0.05, 1.0);
  text('local_data_label_' + i, 'Train / dev', lab.x + 0.14, 6.385, 1.06, 0.25, 14.2, c.data, false, 'center');
  text('local_model_label_' + i, 'Local model', lab.x + 1.55, 6.385, 1.06, 0.25, 14.2, c.model, false, 'center');
  line('local_fit_' + i, lab.x + 1.22, 6.53, lab.x + 1.53, 6.53, c.model, true, 1.35);
  line('parameter_down_' + i, lab.x + 1.20, 5.15, lab.x + 1.20, 5.84, c.model, true, 1.8);
  line('update_up_' + i, lab.x + 1.54, 5.84, lab.x + 1.54, 5.15, c.gate, true, 1.8);
});
text('locality_note', 'Measurements remain within each laboratory', 0.62, 6.99, 8.47, 0.22, 14.4, c.data, false, 'center');

text('outputs_label', 'OUTPUTS', 9.82, 4.44, 1.79, 0.26, 16.6, c.ink, true, 'center');
rect('selected_predictor', 9.86, 4.94, 1.73, 0.88, c.modelFill, c.model, 0.08, 1.0);
text('selected_predictor_label', 'Selected design\n+ fitted predictor', 9.93, 5.06, 1.59, 0.60, 15.2, c.model, false, 'center');
rect('research_history', 9.86, 6.07, 1.73, 0.86, c.researchFill, c.research, 0.08, 1.0);
text('research_history_label', 'Research history\nall trial results', 9.92, 6.20, 1.61, 0.57, 14.7, c.research, false, 'center');

text('tasks_label', 'TASK-SPECIFIC PREDICTORS AND SCORERS', 0.42, 7.48, 11.16, 0.28, 16.2, c.ink, true);
[
  [0.30, 'Drug-target interactions', 'Compound + protein to interaction'],
  [4.20, 'Proteomic efficacy', 'Observed proteome + drug to efficacy'],
  [8.10, 'Cell perturbations', 'Single gene / double gene / drug'],
].forEach(([x, title, body], i) => {
  rect('task_' + i, x, 7.94, 3.60, 0.82, c.neutral, c.rule, 0.08, 1.0);
  slide.addShape(pptx.ShapeType.rect, { x: x + 0.01, y: 8.09, w: 0.055, h: 0.48,
    fill: { color: c.model }, line: { transparency: 100 } });
  text('task_title_' + i, title, x + 0.18, 8.035, 3.27, 0.28, 17.4, c.ink, true);
  text('task_body_' + i, body, x + 0.18, 8.43, 3.27, 0.22, 13.7, c.muted);
});

// The frames and native box labels intentionally overlap their own fill areas.
// Explicitly check connector/text intersections to catch accidental routing errors.
function crossesText(edge, box) {
  const pad = 0.012;
  const l = box.x + pad, r = box.x + box.w - pad;
  const t = box.y + pad, b = box.y + box.h - pad;
  if (Math.abs(edge.x1 - edge.x2) < 1e-8)
    return edge.x1 > l && edge.x1 < r && Math.max(edge.y1, edge.y2) > t && Math.min(edge.y1, edge.y2) < b;
  return edge.y1 > t && edge.y1 < b && Math.max(edge.x1, edge.x2) > l && Math.min(edge.x1, edge.x2) < r;
}
metadata.connector_text_intersections = metadata.edges.flatMap(edge => metadata.text_boxes
  .filter(box => crossesText(edge, box)).map(box => [edge.id, box.id]));
if (metadata.connector_text_intersections.length)
  throw new Error('Connector/text collision: ' + JSON.stringify(metadata.connector_text_intersections));

function orthogonalCrossing(a, b) {
  const av = Math.abs(a.x1 - a.x2) < 1e-8, bv = Math.abs(b.x1 - b.x2) < 1e-8;
  if (av === bv) return false;
  const v = av ? a : b, h = av ? b : a, e = 1e-8;
  return v.x1 > Math.min(h.x1, h.x2) + e && v.x1 < Math.max(h.x1, h.x2) - e &&
    h.y1 > Math.min(v.y1, v.y2) + e && h.y1 < Math.max(v.y1, v.y2) - e;
}
metadata.connector_crossings = metadata.edges.flatMap((edge, index) => metadata.edges.slice(index + 1)
  .filter(other => orthogonalCrossing(edge, other)).map(other => [edge.id, other.id]));
if (metadata.connector_crossings.length) throw new Error('Connector crossing: ' + JSON.stringify(metadata.connector_crossings));

metadata.canvas_overflow = metadata.text_boxes.filter(b => b.x < 0 || b.y < 0 || b.x + b.w > 12 || b.y + b.h > 9);
if (metadata.canvas_overflow.length) throw new Error('Text box exceeds canvas');
metadata.deliberate_enclosures = ['outer_frame', 'inner_frame', 'outputs_frame', 'research_card_*', 'laboratory_*'];
metadata.edition = 'coauthor-review-v2';
fs.writeFileSync(path.join(outDir, 'biocoloop_framework_v2.layout.json'), JSON.stringify(metadata, null, 2) + '\n');
pptx.writeFile({ fileName: path.join(outDir, 'biocoloop_framework_v2.pptx') });
