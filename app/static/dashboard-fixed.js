// ========================================
// Dashboard Interactivo de Cercanías - FIXED
// ========================================

const API_BASE = '';
let map = null;
let mapMarker = null;
let currentStop = null;
let autoRefreshInterval = null;
let searchDebounce = null;

// ========================================
// API Helper
// ========================================
async function api(path) {
  try {
    const res = await fetch(API_BASE + path);
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// ========================================
// Inicialización
// ========================================
document.addEventListener('DOMContentLoaded', async () => {
  console.log('[INIT] Dashboard inicializándose...');
  
  try {
    initializeDatePicker();
    initializeMap();
    initializeTabs();
    initializeDarkMode();
    setupEventListeners();
    await loadStops();
    showToast('Dashboard listo', 'success');
  } catch (error) {
    console.error('[INIT] Error durante la inicialización:', error);
    showToast('Error al inicializar: ' + error.message, 'error');
  }
});

// ========================================
// Date Picker - OBLIGATORIO
// ========================================
function initializeDatePicker() {
  const dateInput = document.getElementById('dateSelect');
  const today = new Date().toISOString().split('T')[0];
  dateInput.value = today;
  dateInput.min = '2020-01-01';
  dateInput.max = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  
  dateInput.addEventListener('change', () => {
    if (!dateInput.value) {
      dateInput.value = today;
      showToast('La fecha es obligatoria', 'warning');
    }
  });
}

// ========================================
// Mapa con Leaflet
// ========================================
function initializeMap() {
  const mapDiv = document.getElementById('map');
  if (!mapDiv) {
    console.warn('[MAP] No se encontró elemento #map');
    return;
  }
  
  try {
    map = L.map('map').setView([40.4168, -3.7038], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(map);
    setTimeout(() => map.invalidateSize(), 300);
    console.log('[MAP] Mapa inicializado');
  } catch (error) {
    console.error('[MAP] Error:', error);
  }
}

function updateMap(lat, lon, name) {
  if (!map) return;
  
  if (mapMarker) {
    map.removeLayer(mapMarker);
  }
  
  map.setView([lat, lon], 15);
  mapMarker = L.marker([lat, lon])
    .addTo(map)
    .bindPopup(`<strong>${name}</strong><br>Lat: ${lat.toFixed(6)}, Lon: ${lon.toFixed(6)}`)
    .openPopup();
  map.invalidateSize();
}

// ========================================
// Sistema de Tabs
// ========================================
function initializeTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  
  console.log(`[TABS] Configurando ${tabButtons.length} tabs`);
  
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      
      // Actualizar botones
      tabButtons.forEach(b => {
        b.classList.remove('tab-active');
        b.classList.add('text-slate-600', 'dark:text-slate-400');
      });
      btn.classList.add('tab-active');
      btn.classList.remove('text-slate-600', 'dark:text-slate-400');
      
      // Actualizar contenido
      tabContents.forEach(content => content.classList.add('hidden'));
      const activeContent = document.getElementById(`tab-${tabId}`);
      if (activeContent) {
        activeContent.classList.remove('hidden');
        if (tabId === 'map' && map) {
          setTimeout(() => map.invalidateSize(), 100);
        }
      }
    });
  });
}

// ========================================
// Dark Mode
// ========================================
function initializeDarkMode() {
  const darkToggle = document.getElementById('darkToggle');
  const themeIcon = document.getElementById('themeIcon');
  const html = document.documentElement;
  
  const savedTheme = localStorage.getItem('theme') || 'light';
  if (savedTheme === 'dark') {
    html.classList.add('dark');
    themeIcon.textContent = 'light_mode';
  }
  
  darkToggle.addEventListener('click', () => {
    html.classList.toggle('dark');
    const isDark = html.classList.contains('dark');
    themeIcon.textContent = isDark ? 'light_mode' : 'dark_mode';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });
}

// ========================================
// Cargar lista de estaciones
// ========================================
async function loadStops() {
  showLoading(true);
  const select = document.getElementById('stopSelect');
  
  try {
    console.log('[STOPS] Cargando estaciones...');
    const response = await api('/stops/names?limit=2000');
    const stops = response.data || [];
    
    console.log(`[STOPS] Recibidas ${stops.length} estaciones`);
    
    select.innerHTML = '<option value="">-- Selecciona una estación --</option>';
    
    stops.forEach(stop => {
      const option = document.createElement('option');
      option.value = stop.stop_id;
      option.textContent = stop.stop_name;
      select.appendChild(option);
    });
    
    showToast(`${stops.length} estaciones cargadas`, 'success');
  } catch (error) {
    console.error('[STOPS] Error:', error);
    select.innerHTML = '<option value="">Error al cargar estaciones</option>';
    showToast('Error al cargar estaciones: ' + error.message, 'error');
  }
  showLoading(false);
}

// ========================================
// Event Listeners
// ========================================
function setupEventListeners() {
  console.log('[EVENTS] Configurando listeners...');
  
  const elements = {
    searchBox: document.getElementById('searchBox'),
    stopSelect: document.getElementById('stopSelect'),
    refreshBtn: document.getElementById('refreshBtn'),
    autoRefreshToggle: document.getElementById('autoRefreshToggle'),
    dateSelect: document.getElementById('dateSelect'),
    prevPage: document.getElementById('prevPage'),
    nextPage: document.getElementById('nextPage')
  };
  
  if (elements.searchBox) {
    elements.searchBox.addEventListener('input', (e) => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => performSearch(e.target.value), 300);
    });
  }
  
  if (elements.stopSelect) {
    elements.stopSelect.addEventListener('change', onStopChange);
  }
  
  if (elements.refreshBtn) {
    elements.refreshBtn.addEventListener('click', refreshData);
  }
  
  if (elements.autoRefreshToggle) {
    elements.autoRefreshToggle.addEventListener('click', toggleAutoRefresh);
  }
  
  if (elements.dateSelect) {
    elements.dateSelect.addEventListener('change', () => {
      if (currentStop) refreshData();
    });
  }
  
  if (elements.prevPage && elements.nextPage) {
    elements.prevPage.addEventListener('click', () => changePage(-1));
    elements.nextPage.addEventListener('click', () => changePage(1));
  }
  
  // Filtro de ruta
  const routeFilter = document.getElementById('routeFilter');
  if (routeFilter) {
    routeFilter.addEventListener('change', () => {
      currentPage = 0;
      displaySchedulePage();
    });
  }
  
  console.log('[EVENTS] Listeners configurados');
}

// ========================================
// Búsqueda de estaciones
// ========================================
async function performSearch(query) {
  const resultsDiv = document.getElementById('searchResults');
  
  if (!query || query.length < 2) {
    resultsDiv.classList.add('hidden');
    return;
  }
  
  try {
    const response = await api(`/stops/search?q=${encodeURIComponent(query)}&limit=20`);
    const stops = response.data || [];
    
    if (stops.length === 0) {
      resultsDiv.innerHTML = '<div class="p-4 text-slate-500">No se encontraron estaciones</div>';
      resultsDiv.classList.remove('hidden');
      return;
    }
    
    resultsDiv.innerHTML = stops.map(stop => `
      <div class="p-3 hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer border-b border-slate-200 dark:border-slate-700 transition-colors"
           onclick="selectStopFromSearch('${stop.stop_id}', '${stop.stop_name.replace(/'/g, "\\'")}')">
        <div class="font-semibold text-slate-800 dark:text-slate-200">${stop.stop_name}</div>
        <div class="text-sm text-slate-500">ID: ${stop.stop_id}</div>
      </div>
    `).join('');
    
    resultsDiv.classList.remove('hidden');
  } catch (error) {
    console.error('[SEARCH] Error:', error);
  }
}

function selectStopFromSearch(stopId, stopName) {
  const select = document.getElementById('stopSelect');
  select.value = stopId;
  document.getElementById('searchBox').value = stopName;
  document.getElementById('searchResults').classList.add('hidden');
  onStopChange();
}

// ========================================
// Cambio de estación seleccionada
// ========================================
async function onStopChange() {
  const stopId = document.getElementById('stopSelect').value;
  if (!stopId) {
    currentStop = null;
    return;
  }
  
  showLoading(true);
  try {
    const response = await api(`/stops/${stopId}`);
    currentStop = response.data;
    
    displayStopInfo(currentStop);
    
    if (currentStop.stop_lat && currentStop.stop_lon) {
      updateMap(
        parseFloat(currentStop.stop_lat),
        parseFloat(currentStop.stop_lon),
        currentStop.stop_name
      );
    }
    
    await refreshData();
    
  } catch (error) {
    console.error('[STOP] Error:', error);
    showToast('Error al cargar la estación', 'error');
  }
  showLoading(false);
}

// ========================================
// Actualizar datos
// ========================================
async function refreshData() {
  if (!currentStop) return;
  
  const stopId = currentStop.stop_id;
  const date = document.getElementById('dateSelect').value;
  
  if (!date) {
    showToast('La fecha es obligatoria', 'warning');
    return;
  }
  
  showLoading(true);
  
  try {
    await loadUpcomingTrains(stopId);
    await loadSchedule(stopId, date);
  } catch (error) {
    console.error('[REFRESH] Error:', error);
    showToast('Error al actualizar datos', 'error');
  }
  
  showLoading(false);
}

// ========================================
// Cargar próximos trenes
// ========================================
async function loadUpcomingTrains(stopId) {
  try {
    const response = await api(`/stops/${stopId}/upcoming?limit=10`);
    const data = response.data;
    
    displayDepartures(data.departures || []);
    displayArrivals(data.arrivals || []);
    
  } catch (error) {
    console.error('[UPCOMING] Error:', error);
    document.getElementById('departuresContent').innerHTML = 
      '<div class="text-center text-red-500 py-4">Error al cargar salidas</div>';
    document.getElementById('arrivalsContent').innerHTML = 
      '<div class="text-center text-red-500 py-4">Error al cargar llegadas</div>';
  }
}

function displayDepartures(departures) {
  const content = document.getElementById('departuresContent');
  const count = document.getElementById('departuresCount');
  
  count.textContent = departures.length;
  
  if (departures.length === 0) {
    content.innerHTML = '<div class="text-center text-slate-500 py-4">No hay salidas próximas</div>';
    return;
  }
  
  content.innerHTML = departures.map(train => {
    const minutes = train.minutes_until || 0;
    const urgentClass = minutes <= 5 ? 'soon' : '';
    const headsign = train.trip_headsign || train.headsign || 'Sin destino';
    const route = train.route_short_name || train.route_id || 'N/A';
    const time = train.departure_time || '--:--:--';
    
    return `
      <div class="train-card bg-white dark:bg-slate-700 rounded-lg p-4 shadow">
        <div class="flex justify-between items-center">
          <div>
            <span class="route-badge">${route}</span>
            <div class="text-sm text-slate-600 dark:text-slate-400 mt-2">
              ${headsign}
            </div>
          </div>
          <div class="text-right">
            <div class="time-badge ${urgentClass}">${minutes} min</div>
            <div class="text-sm text-slate-600 dark:text-slate-400 mt-2">${time}</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function displayArrivals(arrivals) {
  const content = document.getElementById('arrivalsContent');
  const count = document.getElementById('arrivalsCount');
  
  count.textContent = arrivals.length;
  
  if (arrivals.length === 0) {
    content.innerHTML = '<div class="text-center text-slate-500 py-4">No hay llegadas próximas</div>';
    return;
  }
  
  content.innerHTML = arrivals.map(train => {
    const minutes = train.minutes_until || 0;
    const urgentClass = minutes <= 5 ? 'soon' : '';
    const headsign = train.trip_headsign || train.headsign || 'Sin origen';
    const route = train.route_short_name || train.route_id || 'N/A';
    const time = train.arrival_time || '--:--:--';
    
    return `
      <div class="train-card bg-white dark:bg-slate-700 rounded-lg p-4 shadow">
        <div class="flex justify-between items-center">
          <div>
            <span class="route-badge">${route}</span>
            <div class="text-sm text-slate-600 dark:text-slate-400 mt-2">
              ${headsign}
            </div>
          </div>
          <div class="text-right">
            <div class="time-badge ${urgentClass}">${minutes} min</div>
            <div class="text-sm text-slate-600 dark:text-slate-400 mt-2">${time}</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ========================================
// Cargar horarios completos
// ========================================
let currentPage = 0;
const pageSize = 50;

async function loadSchedule(stopId, date) {
  try {
    const response = await api(`/schedule?stop_id=${stopId}&date=${date}&limit=1000`);
    window.allSchedule = response.data || [];
    
    // Llenar el selector de rutas
    const routeFilter = document.getElementById('routeFilter');
    if (routeFilter && window.allSchedule.length > 0) {
      const uniqueRoutes = [...new Set(window.allSchedule
        .map(s => s.route_short_name || s.route_id)
        .filter(Boolean)
      )].sort();
      
      routeFilter.innerHTML = '<option value="">Todas las líneas</option>' +
        uniqueRoutes.map(route => `<option value="${route}">${route}</option>`).join('');
    }
    
    // Actualizar la visualización de rutas en el tab de información
    updateRoutesDisplay();
    
    currentPage = 0;
    displaySchedulePage();
  } catch (error) {
    console.error('[SCHEDULE] Error:', error);
    document.getElementById('scheduleContent').innerHTML = 
      '<div class="text-center text-red-500 py-4">Error al cargar horarios</div>';
  }
}

function displaySchedulePage() {
  const container = document.getElementById('scheduleContent');
  const allSchedule = window.allSchedule || [];
  const routeFilter = document.getElementById('routeFilter');
  const selectedRoute = routeFilter ? routeFilter.value : '';
  
  // Filtrar por ruta si se seleccionó una
  let filteredSchedule = allSchedule;
  if (selectedRoute) {
    filteredSchedule = allSchedule.filter(item => 
      (item.route_short_name === selectedRoute) || (item.route_id === selectedRoute)
    );
  }
  
  if (filteredSchedule.length === 0) {
    container.innerHTML = '<div class="text-center text-slate-500 py-8">No hay horarios disponibles para el filtro seleccionado</div>';
    return;
  }
  
  const start = currentPage * pageSize;
  const end = start + pageSize;
  const page = filteredSchedule.slice(start, end);
  
  const table = `
    <table class="w-full">
      <thead class="bg-slate-100 dark:bg-slate-700">
        <tr>
          <th class="px-4 py-2 text-left">Hora</th>
          <th class="px-4 py-2 text-left">Línea</th>
          <th class="px-4 py-2 text-left">Destino</th>
          <th class="px-4 py-2 text-left">Viaje</th>
        </tr>
      </thead>
      <tbody>
        ${page.map((row, i) => `
          <tr class="${i % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-750'}">
            <td class="px-4 py-2 font-semibold">${row.arrival_time || row.departure_time || '-'}</td>
            <td class="px-4 py-2">
              <span class="route-badge text-xs">${row.route_short_name || '-'}</span>
            </td>
            <td class="px-4 py-2 text-sm text-slate-600 dark:text-slate-400">${row.trip_headsign || '-'}</td>
            <td class="px-4 py-2 text-xs text-slate-500 dark:text-slate-500">${row.trip_id || '-'}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <div class="mt-4 text-center text-sm text-slate-600 dark:text-slate-400">
      ${selectedRoute ? `Mostrando línea ${selectedRoute}: ` : ''}
      ${start + 1} - ${Math.min(end, filteredSchedule.length)} de ${filteredSchedule.length} horarios
      ${selectedRoute && filteredSchedule.length < allSchedule.length ? ` (${allSchedule.length} total)` : ''}
    </div>
  `;
  
  container.innerHTML = table;
}

function changePage(direction) {
  const allSchedule = window.allSchedule || [];
  const routeFilter = document.getElementById('routeFilter');
  const selectedRoute = routeFilter ? routeFilter.value : '';
  
  // Calcular con el filtro aplicado
  let filteredSchedule = allSchedule;
  if (selectedRoute) {
    filteredSchedule = allSchedule.filter(item => 
      (item.route_short_name === selectedRoute) || (item.route_id === selectedRoute)
    );
  }
  
  const maxPage = Math.ceil(filteredSchedule.length / pageSize) - 1;
  currentPage = Math.max(0, Math.min(maxPage, currentPage + direction));
  displaySchedulePage();
}

// ========================================
// Mostrar información de la estación
// ========================================
function displayStopInfo(stop) {
  const infoContent = document.getElementById('infoContent');
  
  infoContent.innerHTML = `
    <div class="space-y-3">
      <div class="p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
        <div class="text-sm text-slate-600 dark:text-slate-400">ID</div>
        <div class="font-semibold text-slate-800 dark:text-slate-200">${stop.stop_id}</div>
      </div>
      <div class="p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
        <div class="text-sm text-slate-600 dark:text-slate-400">Nombre</div>
        <div class="font-semibold text-slate-800 dark:text-slate-200">${stop.stop_name}</div>
      </div>
      ${stop.stop_lat ? `
        <div class="p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
          <div class="text-sm text-slate-600 dark:text-slate-400">Coordenadas</div>
          <div class="font-semibold text-slate-800 dark:text-slate-200">${stop.stop_lat}, ${stop.stop_lon}</div>
        </div>
      ` : ''}
    </div>
  `;
  
  // Ya no necesitamos cargar por separado, usaremos los datos de allSchedule
  updateRoutesDisplay();
}

function updateRoutesDisplay() {
  // Usar los datos ya cargados en allSchedule
  const allSchedule = window.allSchedule || [];
  const uniqueRoutes = [...new Set(allSchedule
    .map(s => s.route_short_name || s.route_id)
    .filter(Boolean)
  )].sort();
  
  const routesContent = document.getElementById('routesContent');
  if (uniqueRoutes.length === 0) {
    routesContent.innerHTML = '<div class="text-slate-500 text-sm">No hay rutas disponibles</div>';
    return;
  }
  
  routesContent.innerHTML = uniqueRoutes.map(route => `
    <span class="inline-block route-badge text-sm m-1">${route}</span>
  `).join('');
}

async function loadRoutesForStop(stopId) {
  // Esta función ya no se usa, pero la dejamos por compatibilidad
  updateRoutesDisplay();
}

// ========================================
// Auto-refresh
// ========================================
function toggleAutoRefresh() {
  const icon = document.getElementById('autoRefreshIcon');
  
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
    icon.textContent = 'pause';
    showToast('Auto-actualización desactivada', 'info');
  } else {
    autoRefreshInterval = setInterval(() => {
      if (currentStop) refreshData();
    }, 30000);
    icon.textContent = 'play_arrow';
    showToast('Auto-actualización activada (30s)', 'success');
  }
}

// ========================================
// UI Helpers
// ========================================
function showLoading(show) {
  const overlay = document.getElementById('loadingOverlay');
  if (show) {
    overlay.classList.remove('hidden');
  } else {
    overlay.classList.add('hidden');
  }
}

function showToast(message, type = 'info') {
  const colors = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-yellow-500',
    info: 'bg-blue-500'
  };
  
  const toast = document.createElement('div');
  toast.className = `fixed bottom-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-slide-in`;
  toast.textContent = message;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px)';
    toast.style.transition = 'all 0.3s ease-out';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
