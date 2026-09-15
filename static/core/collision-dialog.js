const dialog=document.getElementById('collision-dialog');
const iframe=dialog.querySelector('iframe');
const buttons=[...document.querySelectorAll('[data-collision-open]')];
let opener, state={active:false,ready:false}, linked=false;
function sendState(){if(dialog.open&&linked)iframe.contentWindow?.postMessage({type:'collision-link-state',...state},location.origin)}
buttons.forEach(button=>button.addEventListener('click',()=>{
  opener=button;if(dialog.open){dialog.close();return;}
  linked=state.active&&state.ready;
  const url=new URL(iframe.dataset.src,location.href);
  if(linked){url.searchParams.set('age',String(state.age));url.searchParams.set('linked','1')}
  iframe.src=url.href;dialog.showModal();button.setAttribute('aria-expanded','true');
}));
iframe.addEventListener('load',sendState);
dialog.addEventListener('close',()=>{
  iframe.removeAttribute('src');linked=false;
  buttons.forEach(b=>b.setAttribute('aria-expanded','false'));opener?.focus();
});
document.addEventListener('globe-section-state',event=>{
  state=event.detail;
  buttons.forEach(b=>{b.disabled=state.active&&!state.ready});
  if(dialog.open&&linked&&!state.active)dialog.close();else sendState();
});
window.addEventListener('message',event=>{
  if(event.origin!==location.origin||event.source!==iframe.contentWindow)return;
  if(event.data==='close-collision'){dialog.close();return;}
  if(dialog.open&&linked&&state.active&&event.data?.type==='collision-age-change'&&[80,60,40,20,0].includes(event.data.age)){
    document.dispatchEvent(new CustomEvent('globe-section-age',{detail:{age:event.data.age}}));
  }
});
