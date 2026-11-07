const LV = {
  critical:{t:"วิกฤต",c:"#9b4236",r:3}, high:{t:"สูง",c:"#b8793a",r:2},
  watch:{t:"เฝ้าระวัง",c:"#a89a4a",r:1}, normal:{t:"ปกติ",c:"#7d8c70",r:0}
};
const ACTIONS = ["แจ้งทีมดูแลตู้","ปิดตู้ชั่วคราว","ตัดไฟตู้","ย้ายตู้/เงินสด"];
const $ = s => document.querySelector(s);
let D, map, layer, zoneLayer, activeLevel = "", markers = {};
const store = {
  get(){ try{return JSON.parse(localStorage.getItem("atmActions")||"{}")}catch{return {}} },
  set(v){ try{localStorage.setItem("atmActions",JSON.stringify(v))}catch{} }
};

async function load(){
  const res = await fetch("data/status.json?"+Date.now());
  D = await res.json();
  const sel = (id,vals)=>{ const el=$(id), cur=el.value; el.length=1;
    vals.forEach(v=>el.add(new Option(v,v))); el.value=vals.includes(cur)?cur:""; };
  sel("#fRegion",[...new Set(D.atms.map(a=>a.region))]);
  provOptions();
  const d = new Date(D.generated_at);
  $("#meta").textContent = "อัปเดตล่าสุด "+d.toLocaleString("th-TH",{dateStyle:"medium",timeStyle:"short"})+
    " · ตู้ทั้งหมด "+D.atms.length.toLocaleString()+" ตู้";
  const b=$("#banner");
  b.hidden = D.live_data; b.textContent = "ไม่สามารถดึงข้อมูลฝน/น้ำล่าสุดได้ ผลลัพธ์อาจไม่ครบถ้วน";
  render();
}
function provOptions(){
  const r=$("#fRegion").value, el=$("#fProv"), cur=el.value;
  const ps=[...new Set(D.atms.filter(a=>!r||a.region===r).map(a=>a.province))];
  el.length=1; ps.forEach(p=>el.add(new Option(p,p))); el.value=ps.includes(cur)?cur:"";
}
function filtered(){
  const r=$("#fRegion").value,p=$("#fProv").value,only=$("#fOnly").checked;
  return D.atms.filter(a=>(!r||a.region===r)&&(!p||a.province===p)&&
    (!activeLevel||a.level===activeLevel)&&(!only||activeLevel||a.level!=="normal"));
}
function render(){
  const base=D.atms.filter(a=>(!$("#fRegion").value||a.region===$("#fRegion").value)&&(!$("#fProv").value||a.province===$("#fProv").value));
  $("#cards").innerHTML = ["critical","high","watch","normal"].map(k=>{
    const n=base.filter(a=>a.level===k).length;
    return `<button class="card ${activeLevel===k?"on":""}" style="--c:${LV[k].c}" data-k="${k}"><b>${n}</b><span>${LV[k].t}</span></button>`;
  }).join("");
  document.querySelectorAll(".card").forEach(el=>el.onclick=()=>{
    activeLevel = activeLevel===el.dataset.k ? "" : el.dataset.k; render(); });

  const rows = filtered().sort((a,b)=>LV[b.level].r-LV[a.level].r || (a.dist_to_flood_km??99)-(b.dist_to_flood_km??99));
  const acts=store.get();
  $("#count").textContent = `(${rows.length.toLocaleString()} ตู้)`;
  $("#list").innerHTML = rows.length ? rows.slice(0,150).map(a=>`
    <li data-id="${a.id}" style="--c:${LV[a.level].c}"><span class="dot"></span>
      <div><strong>${a.name}</strong>
      <span class="tag">${LV[a.level].t}</span>${acts[a.id]?`<small>✓ ${acts[a.id].join(", ")}</small>`:`<small>${a.reasons[0]}</small>`}</div></li>`).join("")
    : `<div class="empty">ไม่พบตู้ที่ได้รับผลกระทบในตัวกรองนี้</div>`;
  document.querySelectorAll("#list li").forEach(li=>li.onclick=()=>focusAtm(li.dataset.id));
  drawMap(rows);
}
function drawMap(rows){
  if(!map){
    map=L.map("map").setView([13.2,101],6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:18,attribution:"© OpenStreetMap"}).addTo(map);
    zoneLayer=L.layerGroup().addTo(map); layer=L.layerGroup().addTo(map);
    D.zones.forEach(z=>L.circle([z.lat,z.lon],{radius:z.radius_km*1000,color:"#6b7f5e",weight:1,
      fillColor:"#8aa0b0",fillOpacity:.25}).bindTooltip(z.name).addTo(zoneLayer));
  }
  layer.clearLayers(); markers={};
  rows.forEach(a=>{
    const m=L.circleMarker([a.lat,a.lon],{radius:a.level==="critical"?9:7,color:"#fff",weight:2,
      fillColor:LV[a.level].c,fillOpacity:.95}).on("click",()=>focusAtm(a.id)).addTo(layer);
    markers[a.id]=m;
  });
  if(rows.length && !map._fitted){ map.fitBounds(L.latLngBounds(rows.map(a=>[a.lat,a.lon])).pad(.2)); map._fitted=true; }
}
function focusAtm(id){
  const a=D.atms.find(x=>x.id===id); if(!a) return;
  map.setView([a.lat,a.lon],Math.max(map.getZoom(),11));
  const acts=store.get()[id]||[];
  $("#detailBody").innerHTML=`
    <h3>${a.name}</h3>
    <span class="tag" style="--c:${LV[a.level].c}">${LV[a.level].t}</span> <small>${a.id}${a.mock?" · ข้อมูลจำลอง":""}</small>
    <dl>
      <dt>จังหวัด</dt><dd>${a.province} (ภาค${a.region})</dd>
      <dt>ห่างพื้นที่น้ำท่วม</dt><dd>${a.dist_to_flood_km==null?"-":a.dist_to_flood_km+" กม."}</dd>
      <dt>ฝนสะสม 3 วัน</dt><dd>${a.rain3d_mm} มม.</dd>
      <dt>น้ำในแม่น้ำ (เทียบปกติ)</dt><dd>${a.river_ratio} เท่า</dd>
    </dl>
    <strong>สาเหตุที่แจ้งเตือน</strong>
    <ul>${a.reasons.map(r=>`<li>• ${r}</li>`).join("")}</ul>
    <div class="actions">${ACTIONS.map(x=>`<button data-a="${x}" class="${acts.includes(x)?"done":""}">${acts.includes(x)?"✓ ":""}${x}</button>`).join("")}</div>
    <p class="state">บันทึกการดำเนินการไว้ในเครื่องนี้เท่านั้น (รุ่นสาธิต)</p>`;
  $("#detail").hidden=false;
  document.querySelectorAll(".actions button").forEach(b=>b.onclick=()=>{
    const s=store.get(), cur=new Set(s[id]||[]);
    cur.has(b.dataset.a)?cur.delete(b.dataset.a):cur.add(b.dataset.a);
    s[id]=[...cur]; if(!s[id].length) delete s[id]; store.set(s); focusAtm(id); render();
  });
}
$("#close").onclick=()=>$("#detail").hidden=true;
$("#refresh").onclick=load;
$("#fRegion").onchange=()=>{provOptions();render()};
$("#fProv").onchange=render; $("#fOnly").onchange=render;
load().catch(e=>{$("#meta").textContent="โหลดข้อมูลไม่สำเร็จ: "+e.message});
