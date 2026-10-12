const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const state={tab:'productos',data:[],page:0,signal:'todas',loading:false,token:0};
const config={productos:{title:'Productos y juegos',sub:'Compara ofertas de distintas páginas y encuentra nuevas opciones.',placeholder:'Ej. PlayStation 5, laptop gamer...',orders:['Más barato','Más recomendable','Nombre A-Z']},empresas:{title:'Empresas',sub:'Encuentra empresas y servicios dentro de Arequipa o Perú.',placeholder:'Ej. veterinarias, imprentas, ferreterías...',orders:['Más cercanas','Mejor valoradas','Nombre A-Z']},acciones:{title:'Acciones',sub:'Explora indicadores técnicos y tendencias orientativas del mercado.',placeholder:'Ej. AAPL, NVDA o Apple (en una empresa)',orders:['Señal más alcista','Señal más bajista','Nombre A-Z']}};
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const format=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString('es-PE',{maximumFractionDigits:2,minimumFractionDigits:2}):'Sin dato';
const urlSafe=u=>{try{const x=new URL(u);return ['http:','https:'].includes(x.protocol)?x.href:null}catch{return null}};
$('#fecha').textContent=new Intl.DateTimeFormat('es-PE',{day:'numeric',month:'long',year:'numeric'}).format(new Date());
function tabChange(tab){state.tab=tab;state.data=[];state.page=0;state.signal='todas';state.token++;state.loading=false;$('#buscar').disabled=false;$('#buscar span:first-child').textContent='Buscar';const c=config[tab];$('#seccionTitulo').textContent=c.title;$('#seccionSub').textContent=c.sub;$('#consulta').placeholder=c.placeholder;$('#consulta').value='';$('#orden').replaceChildren(...c.orders.map(x=>new Option(x,x)));$('#modoWrap').hidden=tab!=='acciones';$('#stockModes').hidden=tab!=='acciones';$('#zona').parentElement.hidden=tab==='acciones';$('#limiteWrap').hidden=tab==='acciones';$('#disclaimer').hidden=tab!=='acciones';$$('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));$$('[data-senal]').forEach(b=>b.classList.toggle('active',b.dataset.senal==='todas'));$('#contador').textContent='Listo para explorar';render();}
$$('[data-tab]').forEach(b=>b.addEventListener('click',()=>{tabChange(b.dataset.tab);$('#explorar').scrollIntoView({behavior:'smooth'})}));
$('#empezar').addEventListener('click',()=>$('#explorar').scrollIntoView({behavior:'smooth'}));
$$('[data-senal]').forEach(b=>b.addEventListener('click',()=>{state.signal=b.dataset.senal;state.page=0;$$('[data-senal]').forEach(c=>c.classList.toggle('active',c===b));render()}));
$('#orden').addEventListener('change',()=>{state.page=0;render()});$('#modo').addEventListener('change',()=>{$('#consulta').placeholder=$('#modo').value==='Ranking global'?'Opcional: AAPL, NVDA, MSFT':'Ej. AAPL o Apple'});
$('#anterior').addEventListener('click',()=>{state.page=Math.max(0,state.page-1);render();$('#resultados').scrollIntoView({behavior:'smooth',block:'start'})});
$('#siguiente').addEventListener('click',()=>{state.page++;render();$('#resultados').scrollIntoView({behavior:'smooth',block:'start'})});
function itemCard(x, idx){if(state.tab==='productos'){const link=urlSafe(x.link);const price=typeof x.precio_pen==='number'?'S/ '+format(x.precio_pen):x.precio!=null?`${format(x.precio)} ${escapeHtml(x.moneda||'')}`:'Precio no disponible';return `<article class="item" tabindex="0" role="button" data-detalle="${idx}" aria-label="Ver más detalles"><div class="item-top"><span class="tag">PRODUCTO / WEB</span>${x.calificacion!=null?`<span class="score flat">★ ${format(x.calificacion)}</span>`:''}</div><h4>${escapeHtml(x.titulo||'Resultado')}</h4><div class="price">${price}</div><p>${escapeHtml(String(x.resumen||'').slice(0,230))}</p>${link?`<a class="item-link" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">Visitar página ↗</a>`:''}</article>`}
if(state.tab==='empresas'){const link=urlSafe(x.link);return `<article class="item" tabindex="0" role="button" data-detalle="${idx}" aria-label="Ver más detalles"><div class="item-top"><span class="tag">EMPRESA</span>${x.calificacion!=null?`<span class="score flat">★ ${format(x.calificacion)}</span>`:''}</div><h4>${escapeHtml(x.titulo||'Empresa')}</h4><p>📍 ${escapeHtml(x.direccion||'Dirección no disponible')}</p><p>☎ ${escapeHtml(x.telefono||'Teléfono no disponible')}</p>${x.km!=null?`<p>Distancia aproximada desde el centro de Arequipa: ${format(x.km)} km</p>`:''}${x.correos?.length?`<p>✉ ${escapeHtml(x.correos.join(', '))}</p>`:''}${link?`<a class="item-link" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">Sitio web ↗</a>`:''}</article>`}
const score=x.tendencia==='Posible subida'?'up':x.tendencia==='Posible bajada'?'down':'flat';const reasons=(x.razones||[]).slice(0,4).map(z=>escapeHtml(z)).join(' · ');return `<article class="item" tabindex="0" role="button" data-detalle="${idx}" aria-label="Ver más detalles"><div class="item-top"><span class="tag">${escapeHtml(x.ticker||'ACCIÓN')}</span><span class="score ${score}">${escapeHtml(x.tendencia||'Sin señal clara')}</span></div><h4>${escapeHtml(x.empresa||x.ticker)}</h4><div class="price">${format(x.precio)} <span style="font-size:12px;color:#95a1b4">${escapeHtml(x.moneda||'')}</span></div><p>Señal técnica: ${escapeHtml(x.puntuacion)} puntos · RSI: ${format(x.rsi)}</p><p>Variación 20 sesiones: ${x.momento!=null?format(x.momento)+'%':'Sin dato'}${x.potencial!=null?' · Potencial según objetivo de analistas: '+format(x.potencial)+'%':''}</p><div class="reason">${reasons||'Indicadores insuficientes.'}</div></article>`}
function render(){let d=[...state.data],ord=$('#orden').value;if(state.tab==='acciones'){if(state.signal==='subida')d=d.filter(x=>x.tendencia==='Posible subida');if(state.signal==='bajada')d=d.filter(x=>x.tendencia==='Posible bajada');if(state.signal==='neutra')d=d.filter(x=>x.tendencia==='Sin señal clara');d.sort((a,b)=>ord==='Señal más bajista'?a.puntuacion-b.puntuacion:ord==='Nombre A-Z'?String(a.empresa).localeCompare(String(b.empresa)):b.puntuacion-a.puntuacion)}else if(state.tab==='productos'){d.sort((a,b)=>ord==='Nombre A-Z'?String(a.titulo).localeCompare(String(b.titulo)):ord==='Más recomendable'?(b.calificacion??-1)-(a.calificacion??-1):(a.precio_pen??Number.POSITIVE_INFINITY)-(b.precio_pen??Number.POSITIVE_INFINITY))}else{d.sort((a,b)=>ord==='Nombre A-Z'?String(a.titulo).localeCompare(String(b.titulo)):ord==='Mejor valoradas'?(b.calificacion??-1)-(a.calificacion??-1):(a.km??Infinity)-(b.km??Infinity))}state.visible=d;const max=Math.max(1,Math.ceil(d.length/10));state.page=Math.min(state.page,max-1);$('#resultNum').textContent=d.length;$('#contador').textContent=d.length?`${d.length} resultados`:'Listo para explorar';if(!d.length){$('#resultados').innerHTML=`<div class="empty"><div class="empty-illustration">✳</div><b>${state.data.length?'No hay resultados con este filtro':'Las mejores búsquedas comienzan aquí'}</b><p>${state.data.length?'Prueba con otro filtro.':'Introduce una búsqueda para encontrar opciones.'}</p></div>`}else{$('#resultados').innerHTML=d.slice(state.page*10,(state.page+1)*10).map((x,i)=>itemCard(x,state.page*10+i)).join('')}$('#paginacion').hidden=max<=1;$('#paginas').textContent=`Página ${state.page+1} de ${max}`;$('#anterior').disabled=state.page===0;$('#siguiente').disabled=state.page+1>=max;}
// Algunas plataformas devuelven HTML (502/503/504) o cuerpo vacío.
// Nunca asumimos que cualquier respuesta HTTP contiene JSON válido.
async function pedirJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {cache:'no-store', ...options});
  } catch (_) {
    throw new Error('No se pudo contactar al servidor. Comprueba tu conexión y el estado del servicio en Render.');
  }
  const raw = await response.text();
  let data = null;
  try { if (raw.trim()) data = JSON.parse(raw); } catch (_) { /* HTTP del alojamiento, no JSON */ }
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    if ([502,503,504,524].includes(response.status) || response.status >= 500) {
      throw new Error('El servidor se detuvo o demoró demasiado (HTTP '+response.status+'). Revisa los Logs en Render y vuelve a intentar.');
    }
    if (response.status === 404) {
      throw new Error('No se encontró la API. Confirma que Render está ejecutando la última versión del proyecto.');
    }
    throw new Error('El servidor devolvió una respuesta vacía o que no es JSON (HTTP '+response.status+'). Consulta los Logs en Render.');
  }
  if (!response.ok) throw new Error(data.error || 'Error HTTP '+response.status+'.');
  return data;
}

async function esperarBusqueda(jobId, token) {
  const deadline = Date.now() + 145000;
  while (Date.now() < deadline) {
    if (token !== state.token) return null;
    await new Promise(resolve => setTimeout(resolve, 1800));
    if (token !== state.token) return null;
    const datos = await pedirJson('/api/trabajo/' + encodeURIComponent(jobId));
    if (datos.estado === 'terminado') return datos;
    if (datos.estado === 'error') throw new Error(datos.error || 'La búsqueda no pudo completarse.');
    $('#estado').textContent = 'Buscando entre tiendas y fuentes públicas… Puedes seguir esperando; algunas páginas tardan en responder.';
  }
  throw new Error('La búsqueda está tardando demasiado. Prueba con 20 resultados o revisa los Logs en Render.');
}

$('#form').addEventListener('submit', async e => {
  e.preventDefault();
  if (state.loading) return;
  const consulta = $('#consulta').value.trim();
  if (!consulta && !(state.tab === 'acciones' && $('#modo').value === 'Ranking global')) {
    $('#estado').textContent = 'Escribe qué deseas buscar.';
    $('#consulta').focus();
    return;
  }
  state.loading = true;
  const token = ++state.token;
  $('#buscar').disabled = true;
  $('#buscar span:first-child').textContent = 'Buscando…';
  $('#estado').textContent = 'Iniciando la búsqueda en el servidor…';
  $('#resultados').innerHTML = '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
  $('#paginacion').hidden = true;
  const payload = {categoria:state.tab, consulta, zona:$('#zona').value,
                   modo:$('#modo').value, limite:$('#limite').value};
  try {
    let data = await pedirJson('/api/buscar', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)
    });
    if (token !== state.token) return;
    if (data.trabajo) data = await esperarBusqueda(data.trabajo, token);
    if (!data || token !== state.token) return;
    state.data = Array.isArray(data.resultados) ? data.resultados : [];
    state.page = 0;
    render();
    $('#estado').textContent = state.data.length
      ? `Se encontraron ${state.data.length} resultados. Los datos dependen de proveedores externos.`
      : 'No se encontraron resultados. Prueba con otro nombre o menos filtros; algunas páginas limitan el acceso.';
  } catch (err) {
    if (token !== state.token) return;
    state.data = [];
    render();
    $('#estado').textContent = err.message || 'No se pudo completar la consulta.';
  } finally {
    if (token === state.token) {
      state.loading = false;
      $('#buscar').disabled = false;
      $('#buscar span:first-child').textContent = 'Buscar';
    }
  }
});
tabChange('productos');

// Panel de detalle: se abre con toque o Enter y conserva enlaces externos seguros.
const detalles=$('#detalleOverlay');
const safeLink=(url,label)=>{const u=urlSafe(url);return u?`<a class="detail-link" target="_blank" rel="noopener noreferrer" href="${escapeHtml(u)}">${escapeHtml(label)} ↗</a>`:''};
const rowDetail=(lab,val)=>`<div class="detail-row"><span>${escapeHtml(lab)}</span><strong>${escapeHtml(val??'No disponible')}</strong></div>`;
const money=(n,c='')=> n==null?'Sin dato':`${format(n)} ${escapeHtml(c)}`;
function abrirDetalle(idx){const x=state.visible?.[idx];if(!x)return;let out='';
  const title=escapeHtml(x.titulo||x.empresa||x.ticker||'Detalle');
  if(state.tab==='productos'){
    out=`<h2 id="detalleTitulo">${title}</h2><span class="tag">${escapeHtml(x.fuente||'Producto')}</span><p class="detail-intro">${escapeHtml(x.resumen||'No hay descripción disponible en esta fuente.')}</p>
    <div class="detail-group">${rowDetail('Precio original', money(x.precio,x.moneda||''))}${rowDetail('Precio aprox. en soles',x.precio_pen!=null?'S/ '+format(x.precio_pen):'Sin dato')}${rowDetail('Calificación',x.calificacion!=null?format(x.calificacion):'No disponible')}${rowDetail('Reseñas',x.resenas??'No disponible')}${rowDetail('Sitio',x.fuente||'No especificado')}</div>
    <p class="detail-notice">Comprueba el precio, la región de activación, los impuestos y la reputación del vendedor en la página original. Algunas tiendas y Facebook restringen la extracción automática.</p>${safeLink(x.link,'Abrir publicación original')}`;
  }else if(state.tab==='empresas'){
    out=`<h2 id="detalleTitulo">${title}</h2><span class="tag">${escapeHtml(x.fuente||'Empresa')}</span><p class="detail-intro">${escapeHtml(x.resumen||'Información pública encontrada para este negocio.')}</p><div class="detail-group">${rowDetail('Dirección',x.direccion||'No disponible')}${rowDetail('Teléfono',x.telefono||'No disponible')}${rowDetail('Correos',x.correos?.join(', ')||'No disponibles')}${rowDetail('Encargado',x.encargado||'No disponible')}${rowDetail('Valoración',x.calificacion!=null?format(x.calificacion):'No disponible')}${rowDetail('Distancia desde Arequipa',x.km!=null?format(x.km)+' km':'No disponible')}</div>${safeLink(x.link,'Abrir sitio o perfil')}${x.telefono?`<a class="detail-link secondary" href="tel:${escapeHtml(String(x.telefono).replace(/[^+\d]/g,''))}">Llamar ↗</a>`:''}`;
  }else{
    const signal=x.tendencia||'Sin señal clara';const ticker=String(x.ticker||'').toUpperCase();
    out=`<h2 id="detalleTitulo">${title} <small>(${escapeHtml(ticker)})</small></h2><span class="score ${signal==='Posible subida'?'up':signal==='Posible bajada'?'down':'flat'}">${escapeHtml(signal)}</span><div class="detail-price">${money(x.precio,x.moneda||'')}</div><p class="detail-intro">${escapeHtml(x.resumen_empresa||'Evaluación técnica basada en información histórica disponible.')}</p><h3>Indicadores y fundamentos</h3><div class="detail-group">${rowDetail('Puntuación técnica',x.puntuacion)}${rowDetail('RSI de 14 sesiones',format(x.rsi))}${rowDetail('Variación de 20 sesiones',x.momento!=null?format(x.momento)+'%':'Sin dato')}${rowDetail('Media móvil 20',format(x.ma20))}${rowDetail('Media móvil 50',format(x.ma50))}${rowDetail('Objetivo de analistas',money(x.objetivo,x.moneda||''))}${rowDetail('Potencial implícito',x.potencial!=null?format(x.potencial)+'%':'Sin dato')}${rowDetail('Número de analistas',x.analistas??'Sin dato')}${rowDetail('Sector',x.sector||'Sin dato')}${rowDetail('Industria',x.industria||'Sin dato')}${rowDetail('País',x.pais||'Sin dato')}${rowDetail('Capitalización',money(x.capitalizacion,x.moneda||''))}${rowDetail('P/E',format(x.pe))}${rowDetail('Mínimo de 52 semanas',money(x.min52,x.moneda||''))}${rowDetail('Máximo de 52 semanas',money(x.max52,x.moneda||''))}</div><h3>¿Por qué aparece esta señal?</h3><ul class="detail-reasons">${(x.razones||[]).map(t=>`<li>${escapeHtml(t)}</li>`).join('')}</ul><div id="detailChart" class="detail-chart"></div><h3>Consultar o negociar la acción</h3><p class="detail-intro">Estos enlaces te llevan a plataformas externas. Comprar o vender requiere una cuenta aprobada y que el activo esté disponible en tu país.</p>${safeLink('https://www.interactivebrokers.com/es/home.php','Interactive Brokers · bróker')}${safeLink('https://www.tradingview.com/symbols/'+encodeURIComponent(ticker.replace(/[^A-Z0-9.]/g,''))+'/','TradingView · análisis')}${safeLink(x.sitio,'Sitio oficial de la empresa')}<p class="detail-notice">La señal NO es una probabilidad ni una recomendación de compra o venta. Puedes perder dinero. Cotizaciones y objetivos pueden llegar con retraso.</p>`;
  }
  $('#detalleContenido').innerHTML=out;detalles.hidden=false;document.body.classList.add('detail-open');$('#cerrarDetalle').focus();
  if(state.tab==='acciones'&&x.historial?.length)dibujarGrafico(x.historial);
}
function dibujarGrafico(hist){const values=hist.map(x=>Number(x.cierre)).filter(Number.isFinite);if(values.length<2)return;const min=Math.min(...values),max=Math.max(...values),gap=max-min||1;const pts=values.map((v,i)=>`${(i/(values.length-1)*600).toFixed(1)},${(170-(v-min)/gap*150).toFixed(1)}`).join(' ');$('#detailChart').innerHTML=`<p>Últimos ${values.length} cierres disponibles</p><svg viewBox="0 0 600 190" role="img" aria-label="Evolución histórica del precio"><polyline points="${pts}" fill="none" stroke="#356bff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" /></svg><div class="chart-labels"><span>${escapeHtml(hist[0].fecha)}</span><span>${escapeHtml(hist[hist.length-1].fecha)}</span></div>`;}
function cerrarDetalle(){detalles.hidden=true;document.body.classList.remove('detail-open')}
$('#cerrarDetalle').addEventListener('click',cerrarDetalle);$('[data-cerrar]').addEventListener('click',cerrarDetalle);document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!detalles.hidden)cerrarDetalle();if((e.key==='Enter'||e.key===' ')&&e.target.closest('[data-detalle]')){e.preventDefault();abrirDetalle(+e.target.closest('[data-detalle]').dataset.detalle)}});
$('#resultados').addEventListener('click',e=>{if(e.target.closest('a'))return;const card=e.target.closest('[data-detalle]');if(card)abrirDetalle(+card.dataset.detalle)});
