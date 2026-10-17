const {chromium}=require('playwright-core');const fs=require('fs');const path=require('path');
const exe=process.env.PW_CHROMIUM||undefined; // set PW_CHROMIUM to a browser binary if the default is not installed
const T=JSON.parse(fs.readFileSync('timing.json'));
(async()=>{
  const b=await chromium.launch(exe?{executablePath:exe}:{});
  const pg=await b.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1.5});
  await pg.addInitScript(t=>{window.__TIMING__=t},T);
  pg.on('pageerror',e=>console.log('ERR',e.message));
  await pg.goto('file://'+path.resolve('index.html'));
  const mode=process.argv[2];
  if(mode==='stills'){
    fs.mkdirSync('stills',{recursive:true});
    // per scene: points as fraction-of-dur given as args or defaults
    const pts=(process.argv[3]||'0.35,0.6,0.9').split(',').map(Number);
    for(const s of T.scenes){ if(process.argv[4]&&process.argv[4]!==s.id)continue;
      for(const f of pts){const t=s.start+s.dur*f;await pg.evaluate(t=>render(t),t);
        await pg.screenshot({path:`stills/${s.id}_${Math.round(f*100)}.png`})}}
  } else {
    const fps=30,n=Math.ceil(T.total*fps);fs.mkdirSync('frames',{recursive:true});
    for(let i=0;i<n;i++){await pg.evaluate(t=>render(t),i/fps);
      await pg.screenshot({path:`frames/f${String(i).padStart(5,'0')}.jpg`,type:'jpeg',quality:93});
      if(i%300===0)console.log('frame',i,'/',n)}
  }
  await b.close();
})();
