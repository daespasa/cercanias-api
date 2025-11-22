async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error("API error " + res.status);
  return res.json();
}

let page = 0;
let pageSize = 20;
let autoTimer = null;
let map = null;
let mapMarker = null;
let expandedRoutes = new Map();

async function loadNames() {
  const names = await api("/stops/names");
  const sel = document.getElementById("stopSelect");
  // clear existing
  sel.innerHTML = '<option value="">-- seleccionar parada --</option>';
  // Load all stops; show only the name as requested
  (names.data || []).forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.stop_id;
    opt.textContent = s.stop_name || String(s.stop_id);
    sel.appendChild(opt);
  });
}

function debounce(fn, delay = 300) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}

async function doSearch(q) {
  if (!q || q.length < 2) return;
  try {
    const res = await api(`/stops/search?q=${encodeURIComponent(q)}&limit=30`);
    const sel = document.getElementById("stopSelect");
    // present top results as options, but keep existing placeholder
    sel.innerHTML =
      '<option value="">-- seleccionar parada --</option>' +
      (res.data || [])
        .map((s) => `<option value="${s.stop_id}">${s.stop_name}</option>`)
        .join("");
  } catch (e) {
    console.error(e);
  }
}

async function init() {
  await loadNames();
  const sel = document.getElementById("stopSelect");
  sel.addEventListener("change", async () => {
    page = 0;
    await onSelectChange();
  });
  const search = document.getElementById("searchBox");
  if (search) {
    search.addEventListener(
      "input",
      debounce((e) => {
        doSearch(e.target.value);
      }, 250)
    );
  }
  const refresh = document.getElementById("refreshBtn");
  if (refresh) {
    refresh.addEventListener("click", async () => {
      await loadNames();
    });
  }
  const auto = document.getElementById("autoRefresh");
  if (auto) {
    auto.addEventListener("change", () => {
      if (auto.checked) {
        startAuto();
      } else {
        stopAuto();
      }
    });
  }
  document.getElementById("prevPage").addEventListener("click", async () => {
    if (page > 0) {
      page--;
      await onSelectChange();
    }
  });
  document.getElementById("nextPage").addEventListener("click", async () => {
    page++;
    await onSelectChange();
  });
}

function startAuto() {
  stopAuto();
  autoTimer = setInterval(() => {
    const sel = document.getElementById("stopSelect");
    if (sel && sel.value) onSelectChange();
  }, 15_000);
}
function stopAuto() {
  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = null;
  }
}

function refreshAll() {
  // Reload selected stop and any expanded routes
  const sel = document.getElementById("stopSelect");
  if (sel && sel.value) {
    onSelectChange();
  }
  // refresh expanded route panels
  for (const [routeId, node] of expandedRoutes.entries()) {
    fetchRouteStops(routeId, node);
  }
}

async function onSelectChange() {
  const sel = document.getElementById("stopSelect");
  const id = sel.value;
  if (!id) {
    showInfo(null);
    renderSchedule([]);
    return;
  }
  setLoading(true);
  try {
    const stop = await api(`/stops/${id}`);
    showInfo(stop.data || stop);
    // update map if coordinates are present
    const s = stop.data || stop;
    if (s && s.stop_lat && s.stop_lon) {
      updateMap(parseFloat(s.stop_lat), parseFloat(s.stop_lon), s.stop_name);
    }
    const date = document.getElementById("dateSelect")
      ? document.getElementById("dateSelect").value
      : null;
    let schedUrl = `/schedule?stop_id=${encodeURIComponent(
      id
    )}&limit=${pageSize}`;
    if (date) schedUrl += `&date=${encodeURIComponent(date)}`;
    const sched = await api(schedUrl);
    renderSchedule(sched.data || sched);
  } catch (e) {
    document.getElementById("infoContent").textContent = "Error: " + e.message;
    console.error(e);
  }
  setLoading(false);
}

function showInfo(stop) {
  const root = document.getElementById("infoContent");
  root.innerHTML = "";
  if (!stop) {
    root.textContent = "No data";
    return;
  }
  const h = document.createElement("h3");
  h.textContent = stop.stop_name || "Stop";
  root.appendChild(h);
  ["stop_id", "stop_desc", "stop_lat", "stop_lon"].forEach((k) => {
    if (stop[k] !== undefined) {
      const p = document.createElement("p");
      p.textContent = `${k}: ${stop[k]}`;
      root.appendChild(p);
    }
  });
}

function renderSchedule(rows) {
  const root = document.getElementById("scheduleContent");
  root.innerHTML = "";
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  thead.innerHTML =
    "<tr><th>Time</th><th>Trip</th><th>Route</th><th>Headsign</th></tr>";
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  (rows || []).forEach((r) => {
    const tr = document.createElement("tr");
    const t = r.time || r.arrival_time || r.departure_time || "";
    tr.innerHTML = `<td>${t}</td><td>${r.trip_id || ""}</td><td>${
      r.route_short_name || r.route_id || ""
    }</td><td>${r.trip_headsign || ""}</td>`;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  root.appendChild(table);
  // populate routes list from schedule
  const routes = Array.from(
    new Map(
      (rows || []).map((r) => [r.route_id || r.route_short_name, r])
    ).values()
  );
  const routesRoot = document.getElementById("routesContent");
  if (routesRoot) {
    routesRoot.innerHTML = "";
    routes.forEach((rt) => {
      const div = document.createElement("div");
      div.className =
        "mb-3 p-2 rounded-md border border-slate-100 dark:border-slate-700";
      const header = document.createElement("div");
      header.className = "flex items-center justify-between";
      const left = document.createElement("div");
      left.className = "flex items-center gap-3";
      const badge = document.createElement("div");
      badge.className =
        "w-10 h-10 rounded-md bg-slate-700 text-white flex items-center justify-center font-semibold";
      badge.textContent = rt.route_short_name || rt.route_id || "—";
      const txt = document.createElement("div");
      txt.innerHTML = `<div class="font-medium text-sm text-slate-900 dark:text-slate-100">${
        rt.route_long_name || ""
      }</div><div class="text-xs text-slate-500 dark:text-slate-400">${
        rt.route_id || ""
      }</div>`;
      left.appendChild(badge);
      left.appendChild(txt);
      const actions = document.createElement("div");
      const btn = document.createElement("button");
      btn.className =
        "px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-sm";
      btn.textContent = "Ver recorrido";
      actions.appendChild(btn);
      header.appendChild(left);
      header.appendChild(actions);
      div.appendChild(header);
      const container = document.createElement("div");
      container.className =
        "route-stops mt-2 text-sm text-slate-700 dark:text-slate-300";
      div.appendChild(container);
      routesRoot.appendChild(div);

      // wire expand behavior
      btn.addEventListener("click", async () => {
        // toggle
        if (expandedRoutes.has(rt.route_id)) {
          expandedRoutes.delete(rt.route_id);
          container.innerHTML = "";
          return;
        }
        expandedRoutes.set(rt.route_id, container);
        await fetchRouteStops(rt.route_id, container);
      });
    });
  }
}

async function fetchRouteStops(routeId, container) {
  container.innerHTML =
    '<div class="text-xs text-slate-500">Cargando paradas…</div>';
  try {
    const res = await api(`/routes/${encodeURIComponent(routeId)}/stops`);
    const rows = res.data || [];
    // group by direction_id
    const grouped = rows.reduce((acc, r) => {
      const k = String(r.direction_id || 0);
      (acc[k] || (acc[k] = [])).push(r);
      return acc;
    }, {});
    container.innerHTML = "";
    Object.keys(grouped)
      .sort()
      .forEach((dir) => {
        const title = document.createElement("div");
        title.className = "font-semibold mt-2";
        title.textContent = dir === "0" ? "Ida" : "Vuelta";
        container.appendChild(title);
        const list = document.createElement("ol");
        list.className = "pl-4 mt-1";
        grouped[dir].forEach((s) => {
          const li = document.createElement("li");
          li.className = "py-1";
          li.textContent = `${s.stop_name || s.stop_id}`;
          list.appendChild(li);
        });
        container.appendChild(list);
      });
  } catch (e) {
    container.innerHTML =
      '<div class="text-xs text-red-500">Error al cargar paradas</div>';
    console.error(e);
  }
}

function setLoading(on) {
  const s = document.getElementById("spinner");
  if (!s) return;
  s.style.display = on ? "inline" : "none";
}

window.addEventListener("load", () => {
  init().catch((e) => {
    console.error(e);
    const info = document.getElementById("infoContent");
    if (info) info.textContent = "Failed to load: " + e.message;
  });
});
// Force dark theme only
try {
  document.documentElement.classList.add("dark");
} catch (e) {}
// hide dark toggle if present
try {
  const dt = document.getElementById("darkToggle");
  if (dt) dt.style.display = "none";
} catch (e) {}

// Map helpers (Leaflet must be loaded via CDN in HTML)
function ensureMap() {
  if (map || typeof L === "undefined") return;
  try {
    map = L.map("map", { attributionControl: true }).setView(
      [40.4168, -3.7038],
      6
    );
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
  } catch (e) {
    console.warn("Leaflet not available", e);
    map = null;
  }
}

function updateMap(lat, lon, label) {
  ensureMap();
  if (!map) return;
  const ll = [lat, lon];
  map.setView(ll, Math.max(map.getZoom(), 13));
  if (mapMarker) {
    mapMarker.setLatLng(ll);
    mapMarker.bindPopup(label || "").openPopup();
  } else {
    mapMarker = L.marker(ll)
      .addTo(map)
      .bindPopup(label || "")
      .openPopup();
  }
}

// initialize map early so tiles can load
window.addEventListener("load", () => {
  try {
    ensureMap();
  } catch (e) {
    /* ignore */
  }
});
