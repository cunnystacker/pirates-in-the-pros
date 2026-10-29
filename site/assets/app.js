
(function(){var t=document.getElementById('roster-table');if(!t)return;var tb=t.tBodies[0];
var fl=document.getElementById('fLevel'),ft=document.getElementById('fType'),fs=document.getElementById('fStatus');
function apply(){[].forEach.call(tb.rows,function(r){var ok=(!fl.value||r.dataset.level===fl.value)&&(!ft.value||r.dataset.type===ft.value)&&(!fs.value||(fs.value==='released'?r.dataset.status!=='active':r.dataset.status===fs.value));r.style.display=ok?'':'none';});}
[fl,ft,fs].forEach(function(e){e.addEventListener('change',apply)});apply();
[].forEach.call(t.tHead.rows[0].cells,function(th,i){th.addEventListener('click',function(){var asc=!th.classList.contains('asc');[].forEach.call(t.tHead.rows[0].cells,function(c){c.classList.remove('asc','desc')});th.classList.add(asc?'asc':'desc');
var rows=[].slice.call(tb.rows);rows.sort(function(a,b){var x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;var nx=parseFloat(x),ny=parseFloat(y);var c=(!isNaN(nx)&&!isNaN(ny))?nx-ny:(x||'~').localeCompare(y||'~');return asc?c:-c});rows.forEach(function(r){tb.appendChild(r)});});});})();
function pipSignup(f){var m=f.querySelector('.formmsg'),b=f.querySelector('button');if(f.getAttribute('action')==='#'){m.textContent="Thanks! Sign-ups open soon.";return false}b.disabled=true;fetch(f.action,{method:'POST',mode:'no-cors',body:new FormData(f)}).then(function(){m.textContent="You're in! Check your inbox to confirm.";f.reset()}).catch(function(){m.textContent="Hmm, that didn't go through. Try again?"}).finally(function(){b.disabled=false});return false}
