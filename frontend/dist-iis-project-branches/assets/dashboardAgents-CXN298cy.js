function p(s,r=3){return s.filter(e=>{var t;return((t=e.department)==null?void 0:t.trim().toLowerCase())==="support"&&e.assigned>0}).slice(0,r)}export{p as s};
