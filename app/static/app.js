async function refresh() {
  try {
    const res = await fetch('/api/cameras');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const list = await res.json();
    console.log('Camera list:', list);

    const wrap = document.getElementById('cam-list');
    wrap.innerHTML = '';

    if (!Array.isArray(list)) {
      wrap.innerHTML = `<p class="has-text-danger">Unexpected response from server</p>`;
      return;
    }

    list.forEach(cam => {
      const btn = document.createElement('button');
      btn.className = 'button is-light';
      btn.innerText = cam.name;
      btn.onclick = () => {
        const safeId = cam.id.startsWith('/') ? cam.id.slice(1) : cam.id;
        const encodedId = encodeURIComponent(safeId);
        fetch(`/api/stream/${encodedId}/start`, { method: 'POST' });
      };
      wrap.appendChild(btn);
    });
  } catch (err) {
    console.error('Failed to fetch cameras:', err);
  }
}

window.onload = refresh;