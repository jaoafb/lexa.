/** Typography controls and stable reading anchor while the settings sheet is open. */
export function setupReadingPreferences({reading,controls,sheet,readingPreferences,storageWrite,toast,getPanelState}){
 function applyPreferences(){
  reading.style.setProperty('--reading-size',readingPreferences.size+'px');
  reading.dataset.spacing=readingPreferences.spacing;
  document.querySelector('#reading-spacing').value=readingPreferences.spacing;
  document.querySelector('#font-size').textContent=readingPreferences.size+' px';
  document.querySelector('#font-down').disabled=readingPreferences.size===16;
  document.querySelector('#font-up').disabled=readingPreferences.size===26;
 }
 function readingAnchor(){
  const line=controls.getBoundingClientRect().bottom+12;
  // Use the same visible normative unit as the reader-continuity check.
  // A heading immediately above it is not a stable anchor when line spacing changes.
  const units=[...document.querySelectorAll('#articles .legal-unit')];
  const element=units.find(el=>el.getBoundingClientRect().bottom>line)
   ||[...document.querySelectorAll('#articles .article-heading')].find(el=>el.getBoundingClientRect().bottom>line);
  return element?{element,top:element.getBoundingClientRect().top}:null;
 }
 function savePreferences(){
  const anchor=sheet.open?readingAnchor():null;
  applyPreferences();
  const panelState=getPanelState();
  if(anchor&&panelState){
   panelState.y+=anchor.element.getBoundingClientRect().top-anchor.top;
   document.body.style.top=-panelState.y+'px';
  }
  if(!storageWrite('lexa-reading',readingPreferences))toast('Ajustes temporários: armazenamento indisponível');
 }
 document.querySelector('#reading-spacing').onchange=e=>{readingPreferences.spacing=e.target.value;savePreferences();};
 document.querySelector('#reset-reading').onclick=()=>{readingPreferences.size=19;readingPreferences.spacing='standard';savePreferences();};
 document.querySelector('#font-down').onclick=()=>{readingPreferences.size=Math.max(16,readingPreferences.size-1);savePreferences();};
 document.querySelector('#font-up').onclick=()=>{readingPreferences.size=Math.min(26,readingPreferences.size+1);savePreferences();};
 return {applyPreferences};
}
