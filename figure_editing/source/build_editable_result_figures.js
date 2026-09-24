/* Editable PowerPoint counterparts of the active BioCoLoop result figures.
 * Each panel is a native chart with an embedded spreadsheet. No bitmap plots.
 * Rebuild: node build_editable_result_figures.js
 * Dependency: npm install pptxgenjs@3.12.0 (jszip is its dependency).
 * Values are loaded from result_figure_data.json, generated from the verified
 * publication snapshot on first use. Never edit research values for styling.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert');
function dependency(name) {
  try { return require(name); } catch (_) {
    return require('/liziqing/yukai/GOAI/research/cpi_ppi_slides_20260918/work/node_modules/' + name);
  }
}
const pptxgen = dependency('pptxgenjs');
const JSZip = dependency('jszip');
const ROOT = __dirname;
const PAPER = path.resolve(ROOT, '../..');
const DATA = path.join(ROOT, 'result_figure_data.json');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const tasks = [
  ['native_tapb', 'DTI', 'AUROC'], ['ptpc_neural', 'Proteomics', 'AP'],
  ['vcc_corrected', 'VCC', 'Top-1'], ['norman_double_corrected', 'Norman', 'Top-1'],
  ['tahoe_drug_corrected', 'Tahoe', 'Top-1'],
];
const colors = {qwen:'2166AC', luna:'B35806'};
const FONT = 'DejaVu Sans';

function extract() {
  const src = path.join(PAPER, 'tables/completed_ablation/snapshot.json');
  const buf = fs.readFileSync(src), snapshot = JSON.parse(buf);
  const expected = JSON.parse(fs.readFileSync(path.join(PAPER,'tables/completed_ablation/provenance.json')))
    .outputs_sha256['paper/tables/completed_ablation/snapshot.json'];
  assert.equal(hash(buf), expected, 'Publication snapshot hash mismatch');
  const out = {source:'tables/completed_ablation/snapshot.json',source_sha256:hash(buf),
    score_scale:'Original metric multiplied by 100, with no rounding',
    laboratory_x_axis:'Categorical: the tested settings 1, 2, 5, 10 are equally spaced',
    search_x_axis:'Numeric proposal count; irregular held-out prefixes retain their actual spacing',
    laboratory:[],short6:[],long24:[]};
  for (const [task,title,metric] of tasks) {
    const series = ['participation','partition'].map((family,i) => {
      const row=snapshot.laboratory.find(r=>r.task===task && r.family===family);
      const samples=[1,2,5,10].map(k=>row.by_k[String(k)].map(v=>100*v));
      return {name:i?'Fixed data pool':'More clients + data',family,
        color:i?'B5632E':'2463A5',dash:!!i,marker:i?'square':'circle',
        x:[1,2,5,10],y:samples.map(s=>s.reduce((a,b)=>a+b,0)/s.length),samples};
    });
    out.laboratory.push({task,title,metric,series});
  }
  for(const protocol of ['short6','long24']) {
    for(const role of ['development','heldout']) {
      for(const [task,title,metric] of (protocol==='short6'?tasks:tasks.slice(1))) {
        const series=[];
        // Same plotting order as the manuscript: loop first, direct above it.
        for(const backend of ['qwen','luna']) for(const mode of ['loop','direct']) {
          const run=snapshot.loops.find(r=>r.protocol===protocol&&r.task===task&&r.backend===backend);
          const x=role==='development'?run.modes[mode].trajectory.map(p=>p.slot):run.prefixes.map(p=>p.budget);
          const y=role==='development'?run.modes[mode].trajectory.map(p=>100*p.primary):run.prefixes.map(p=>100*p[mode+'_heldout_primary']);
          assert.equal(run.slots,protocol==='short6'?6:24);
          assert(x.length===y.length&&y.every(Number.isFinite));
          series.push({name:(backend==='qwen'?'Qwen':'Luna')+' '+mode,
            backend,mode,seed:run.seed,color:colors[backend],dash:mode==='direct',
            marker:mode==='direct'?'x':'circle',x,y});
        }
        out[protocol].push({task,title,metric,role,series});
      }
    }
  }
  fs.writeFileSync(DATA,JSON.stringify(out,null,2)+'\n');
  return out;
}
const data=fs.existsSync(DATA)?JSON.parse(fs.readFileSync(DATA)):extract();

function deck(w,h) {
  const p=new pptxgen();
  p.defineLayout({name:'PAPER_FIGURE',width:w,height:h}); p.layout='PAPER_FIGURE';
  p.author='BioCoLoop authors';p.subject='Editable publication figure';
  p.title='BioCoLoop editable result figure';p.company='';p.lang='en-US';
  p.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'en-US'};
  const slide=p.addSlide();slide.background={color:'FFFFFF'};
  return {p,slide,panels:[],w,h};
}
function text(slide,t,x,y,w,h,size=15,extra={}) {
  slide.addText(t,{x,y,w,h,fontFace:FONT,fontSize:size,color:'111111',margin:0,
    breakLine:false,align:'center',valign:'mid',...extra});
}
function niceAxis(series, n=3) {
  let v=series.flatMap(s=>s.y),lo=Math.min(...v),hi=Math.max(...v);
  let span=hi-lo;if(span<1e-10)span=Math.max(1,Math.abs(lo)*.045);
  const raw=span/(n-1),m=Math.pow(10,Math.floor(Math.log10(raw)));
  const step=[1,2,2.5,5,10].map(x=>x*m).find(x=>x>=raw)||10*m;
  let min=Math.floor((lo-span*.12)/step)*step,max=Math.ceil((hi+span*.12)/step)*step;
  if(min===max){min-=step;max+=step;}
  return {min,max,step,format:step<.1?'0.00':!Number.isInteger(step)?'0.0':'0'};
}
function panel(d,model,x,y,w,h,opts={}) {
  const axis=niceAxis(model.series,opts.ticks||3);
  const isLab=!!opts.laboratory;
  const series=isLab?model.series.map(s=>({name:s.name,labels:s.x.map(String),values:s.y})):
    [{name:'Proposal slots',values:model.series[0].x},...model.series.map(s=>({name:s.name,values:s.y}))];
  const options={x,y,w,h,showTitle:false,showLegend:false,showValue:false,
    chartColors:model.series.map(s=>s.color),showBorder:false,showCatName:false,
    chartArea:{fill:{color:'FFFFFF'},border:{color:'FFFFFF',pt:0}},
    plotArea:{fill:{color:'FFFFFF'},border:{color:'FFFFFF',pt:0}},
    layout:{x:.29,y:.05,w:.68,h:.77},
    catAxisLabelFontFace:FONT,catAxisLabelFontSize:opts.font||13,
    valAxisLabelFontFace:FONT,valAxisLabelFontSize:opts.font||13,
    catAxisLabelColor:'111111',valAxisLabelColor:'111111',
    catAxisLineColor:'111111',valAxisLineColor:'111111',
    catAxisLineSize:1,valAxisLineSize:1,
    catAxisMajorTickMark:'out',valAxisMajorTickMark:'out',
    catAxisMinorTickMark:'none',valAxisMinorTickMark:'none',
    valAxisMinVal:axis.min,valAxisMaxVal:axis.max,valAxisMajorUnit:axis.step,
    valAxisLabelFormatCode:axis.format,valLabelFormatCode:axis.format,
    catAxisLabelPos:opts.hideX?'none':'low',valAxisLabelPos:'low',
    valGridLine:{color:'D9DEE5',width:.65,style:'solid'},
    catGridLine:{color:isLab?'FFFFFF':'D9DEE5',width:isLab?0:.65,style:'solid'},
    lineSize:2.2,lineDataSymbol:'circle',lineDataSymbolSize:5,
    lineDataSymbolLineSize:12700,lineSmooth:false,showMarker:true,
    showCatAxisTitle:false,showValAxisTitle:false,
    showSerName:false,showLeaderLines:false,
    catAxisCrossesAt:isLab?1:0,valAxisCrossesAt:axis.min,
  };
  if(!isLab)Object.assign(options,{catAxisMinVal:0,catAxisMaxVal:opts.slots,
    catAxisMajorUnit:opts.slots===6?2:6,catLabelFormatCode:'0'});
  d.slide.addChart(isLab?d.p.ChartType.line:d.p.ChartType.scatter,series,options);
  d.panels.push({model,kind:isLab?'line':'scatter',bounds:{x,y,w,h},axis,hideX:!!opts.hideX});
}
function legend(slide,items,y,totalW,font=14) {
  const widths=items.map(s=>.6+s.name.length*font/130),sum=widths.reduce((a,b)=>a+b,0)+.28*(items.length-1);
  let x=(totalW-sum)/2;
  for(let i=0;i<items.length;i++) {
    const s=items[i],ly=y+.12;
    slide.addShape('line',{x,y:ly,w:.42,h:0,line:{color:s.color,width:2.3,dashType:s.dash?'dash':'solid'}});
    if(s.marker==='x'){
      slide.addShape('line',{x:x+.18,y:ly-.045,w:.09,h:.09,line:{color:s.color,width:1.5}});
      slide.addShape('line',{x:x+.18,y:ly+.045,w:.09,h:-.09,line:{color:s.color,width:1.5}});
    } else slide.addShape(s.marker==='square'?'rect':'ellipse',{x:x+.17,y:ly-.04,w:.08,h:.08,
      line:{color:s.color,width:1.2},fill:{color:s.marker==='square'?s.color:'FFFFFF'}});
    text(slide,s.name,x+.50,y-.02,widths[i]-.50,.29,font,{align:'left'});x+=widths[i]+.28;
  }
}
function loopLegend(d){
  const sample=d.panels[0].model.series;
  legend(d.slide,[sample[1],sample[0],sample[3],sample[2]],.07,d.w,13.2);
}
function laboratory(){
  const d=deck(15,4.4),pw=2.89;
  data.laboratory.forEach((m,i)=>{
    const x=.25+i*pw;
    text(d.slide,m.title+'\n'+m.metric,x+.69,.15,2.05,.64,20);
    panel(d,m,x,.83,pw,2.83,{laboratory:true,font:17});
    text(d.slide,'K',x+1.45,3.47,.5,.35,18);
  });
  text(d.slide,'Score (%)',.005,1.35,.34,1.55,18,{vert:'vert270'});
  legend(d.slide,data.laboratory[0].series,3.94,15,19);
  return d;
}
function short(){
  const d=deck(11,6),pw=2.12;
  for(const m of data.short6){
    const col=tasks.findIndex(t=>t[0]===m.task),row=m.role==='development'?0:1;
    const x=.32+col*pw,y=row===0?1.13:3.44;
    if(row===0)text(d.slide,m.title+'\n'+m.metric+' ×100',x+.4,.61,1.7,.52,14.4);
    panel(d,m,x,y,pw,2.04,{slots:6,font:12.8,hideX:row===0});
  }
  loopLegend(d);
  text(d.slide,'Development',.03,1.45,.32,1.47,14.2,{vert:'vert270'});
  text(d.slide,'Held-out',.03,3.92,.32,1.15,14.2,{vert:'vert270'});
  text(d.slide,'Proposal slots (0 = initial design)',2.0,5.60,7.8,.30,14);
  return d;
}
function extended(){
  const d=deck(11,13),pw=3.46,ph=2.60;
  for(const m of data.long24){
    const ti=tasks.slice(1).findIndex(t=>t[0]===m.task),role=m.role==='development'?0:1;
    const col=ti%3,row=2*role+Math.floor(ti/3),x=.32+col*pw,y=.83+row*3.10;
    text(d.slide,(m.task==='ptpc_neural'?'PTPC':m.title)+(role?' / heldout':' / dev.'),x+.48,y-.31,2.88,.30,17);
    panel(d,m,x,y,pw,ph,{slots:24,font:14,ticks:4});
    text(d.slide,'Proposal slots',x+.85,y+2.44,2.24,.25,15.4);
    text(d.slide,(m.task==='ptpc_neural'?'AP':'Macro Top-1')+' ×100',x+.015,y+.32,.29,1.62,15.4,{vert:'vert270'});
  }
  loopLegend(d);return d;
}
function unescapeXml(s){return s.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>');}
function cacheValues(xml,tag){
  const block=xml.match(new RegExp('<c:'+tag+'>([\\s\\S]*?)</c:'+tag+'>'));
  assert(block,'Missing '+tag);
  return [...block[1].matchAll(/<c:pt idx="\d+"><c:v>([^<]+)<\/c:v><\/c:pt>/g)].map(m=>Number(m[1]));
}
async function save(d,filename){
  const target=path.join(ROOT,filename);
  await d.p.writeFile({fileName:target});
  const zip=await JSZip.loadAsync(fs.readFileSync(target));
  const chartPaths=Object.keys(zip.files).filter(n=>/^ppt\/charts\/chart\d+\.xml$/.test(n))
    .sort((a,b)=>Number(a.match(/chart(\d+)/)[1])-Number(b.match(/chart(\d+)/)[1]));
  for(let k=0;k<d.panels.length;k++){
    const chartPath=chartPaths[k],p=d.panels[k];
    const rel=await zip.file('ppt/charts/_rels/'+path.basename(chartPath)+'.rels').async('string');
    const workbookTarget=rel.match(/Target="([^"]+\.xlsx)"/)[1];
    const workbookPath=path.posix.normalize(path.posix.join('ppt/charts',workbookTarget));
    const workbook=await JSZip.loadAsync(await zip.file(workbookPath).async('nodebuffer'));
    const sheet=await workbook.file('xl/worksheets/sheet1.xml').async('string');
    const shared=await workbook.file('xl/sharedStrings.xml').async('string');
    const strings=[...shared.matchAll(/<si>([\s\S]*?)<\/si>/g)].map(m=>
      [...m[1].matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(t=>unescapeXml(t[1])).join(''));
    const cells={};
    for(const cell of sheet.matchAll(/<c r="([A-Z]+\d+)"([^>]*)><v>([^<]+)<\/v><\/c>/g))
      cells[cell[1]]=cell[2].includes('t="s"')?strings[Number(cell[3])]:Number(cell[3]);
    p.model.series.forEach((series,j)=>{
      const col=String.fromCharCode(66+j);
      assert.equal(cells[col+'1'],series.name,'Workbook series name mismatch');
      series.y.forEach((v,i)=>assert.equal(cells[col+(i+2)],v,'Workbook Y differs from chart/source'));
    });
    p.model.series[0].x.forEach((v,i)=>assert.equal(
      cells['A'+(i+2)],p.kind==='line'?String(v):v,'Workbook X differs from chart/source'));
    let xml=await zip.file(chartPath).async('string'),idx=0;
    xml=xml.replace(/<c:ser>[\s\S]*?<\/c:ser>/g,part=>{
      const s=p.model.series[idx++]; assert(s);
      // PptxGenJS exposes line styling per chart. These OOXML-only style
      // adjustments preserve native charts and their embedded data workbooks.
      const y=cacheValues(part,p.kind==='scatter'?'yVal':'val');
      assert.deepStrictEqual(y,s.y,'Y cache differs from verified snapshot');
      if(p.kind==='scatter')assert.deepStrictEqual(cacheValues(part,'xVal'),s.x);
      part=part.replace(/<a:prstDash val="[^"]+"\/>/,'<a:prstDash val="'+(s.dash?'dash':'solid')+'"/>');
      part=part.replace(/<c:marker>[\s\S]*?<\/c:marker>/,marker=>{
        marker=marker.replace(/<c:symbol val="[^"]+"\/>/,'<c:symbol val="'+s.marker+'"/>');
        if(p.kind==='scatter'||s.marker==='circle')marker=marker.replace(/<a:solidFill>[\s\S]*?<\/a:solidFill>/,'<a:noFill/>');
        return marker;
      });
      return part;
    });
    // The library hardcodes scatter tick placement and links x formats to the
    // y-value workbook format. Explicit axis formatting keeps x as integers.
    xml=xml.replace(/<c:(valAx|catAx)>[\s\S]*?<\/c:\1>/g,axis=>{
      const isX=axis.includes('<c:axPos val="b"/>');
      axis=axis.replace(/<c:tickLblPos val="[^"]+"\/>/,
        '<c:tickLblPos val="'+(isX&&p.hideX?'none':'low')+'"/>');
      if(isX)axis=axis.replace(/<c:numFmt [^>]+\/>/,'<c:numFmt formatCode="0" sourceLinked="0"/>');
      return axis;
    });
    assert.equal(idx,p.model.series.length);zip.file(chartPath,xml);
  }
  const pptx=await zip.generateAsync({type:'nodebuffer',compression:'DEFLATE'});
  fs.writeFileSync(target,pptx);
  const charts=Object.keys(zip.files).filter(n=>/^ppt\/charts\/chart\d+\.xml$/.test(n));
  const workbooks=Object.keys(zip.files).filter(n=>/^ppt\/embeddings\/.*\.xlsx$/.test(n));
  const images=Object.keys(zip.files).filter(n=>/^ppt\/media\//.test(n)&&!zip.files[n].dir);
  assert.equal(charts.length,d.panels.length);assert.equal(workbooks.length,d.panels.length);assert.equal(images.length,0);
  return {filename,sha256:hash(pptx),slide_size_inches:[d.w,d.h],slides:1,
    charts:charts.length,embedded_editable_workbooks:workbooks.length,bitmap_images:0,
    plotted_series:d.panels.reduce((s,p)=>s+p.model.series.length,0),
    plotted_points:d.panels.reduce((s,p)=>s+p.model.series.reduce((t,m)=>t+m.y.length,0),0),
    exact_numeric_chart_cache_verification:true,
    exact_embedded_workbook_verification:true,
    panels:d.panels.map(p=>({task:p.model.task,role:p.model.role||'laboratory',kind:p.kind,bounds:p.bounds,axis:p.axis}))};
}
(async()=>{
  const outputs=[];
  outputs.push(await save(laboratory(),'Figure_3_laboratory_count.pptx'));
  outputs.push(await save(short(),'Figure_4_short_loop.pptx'));
  outputs.push(await save(extended(),'Figure_5_extended_loop.pptx'));
  const receipt={source:data.source,source_sha256:data.source_sha256,data_sha256:hash(fs.readFileSync(DATA)),
    authoring_source_sha256:hash(fs.readFileSync(__filename)),
    original_manuscript_and_source_data_unchanged:true,outputs,
    visual_review_status:'PENDING: render the three decks before handoff'};
  fs.writeFileSync(path.join(ROOT,'result_figures_integrity.json'),JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify(outputs.map(({filename,charts,embedded_editable_workbooks,plotted_series,plotted_points})=>
    ({filename,charts,embedded_editable_workbooks,plotted_series,plotted_points})),null,2));
})().catch(e=>{console.error(e);process.exit(1);});
