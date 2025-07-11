async function refresh() {
  const list = await fetch('/api/cameras').then(r => r.json());
  const wrap = document.getElementById('cam-list');
  wrap.innerHTML = '';
  list.forEach(cam => {
    const btn = document.createElement('button');
    btn.className = 'button is-light';
    btn.innerText = `${cam.name}`;
    btn.onclick = () => fetch(`/api/stream/${encodeURIComponent(cam.id)}/start`, {method: 'POST'});
    wrap.appendChild(btn);
  });
}
window.onload = refresh;