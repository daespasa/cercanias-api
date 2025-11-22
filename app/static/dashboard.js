// ========================================
// Dashboard Interactivo de Cercanías
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
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// ========================================
// Inicialización
// ========================================
document.addEventListener('DOMContentLoaded', async () => {
  console.log('Dashboard inicializándose...');
  
  try {
    initializeDatePicker();
    console.log('Date picker inicializado');
    
    initializeMap();
    console.log('Mapa inicializado');
    
    initializeTabs();
    console.log('Tabs inicializadas');
    
    initializeDarkMode();
    console.log('Dark mode inicializado');
    
    setupEventListeners();
    console.log('Event listeners configurados');
    
    await loadStops();
    console.log('Estaciones cargadas');
    
    // Mensaje de bienvenida
    showToast('Bienvenido al Dashboard de Cercanías', 'info');
  } catch (error) {
    console.error('Error durante la inicialización:', error);
    showToast('Error al inicializar el dashboard', 'error');
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
  if (!mapDiv) return;
  
  map = L.map('map').setView([40.4168, -3.7038], 6); // Madrid centro por defecto
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map);
  
  // Pequeño delay para que el mapa se renderice bien
  setTimeout(() => map.invalidateSize(), 300);
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
  
  console.log(`Encontrados ${tabButtons.length} botones de tabs`);
  console.log(`Encontrados ${tabContents.length} contenidos de tabs`);
  
  tabButtons.forEach((btn, index) => {
    console.log(`Configurando tab ${index}:`, btn.getAttribute('data-tab'));
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      console.log('Tab clickeada:', tabId);
      
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
        
        // Si es el tab de mapa, actualizar tamaño
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
  
  // Cargar preferencia guardada
  const savedTheme = localStorage.getItem('theme') || 'light';
  if (savedTheme === 'dark') {
    html.classList.add('dark');
    themeIcon.textContent = '☀️';
  }
  
  darkToggle.addEventListener('click', () => {
    html.classList.toggle('dark');
    const isDark = html.classList.contains('dark');
    themeIcon.textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });
}

// ========================================
// Cargar lista de estaciones
// ========================================
async function loadStops() {
  showLoading(true);
  try {
    console.log('Cargando estaciones desde /stops/names...');
    const response = await api('/stops/names?limit=1000');
    const stops = response.data || [];
    
    console.log(`Recibidas ${stops.length} estaciones`);
    
    const select = document.getElementById('stopSelect');
    if (!select) {
      console.error('No se encontró el elemento stopSelect');
      return;
    }
    
    select.innerHTML = '<option value="">-- Selecciona una estación --</option>';
    
    stops.forEach(stop => {
      const option = document.createElement('option');
      option.value = stop.stop_id;
      option.textContent = stop.stop_name;
      select.appendChild(option);
    });
    
    console.log(`Selector actualizado con ${stops.length} opciones`);
    showToast(`${stops.length} estaciones cargadas`, 'success');
  } catch (error) {
    console.error('Error loading stops:', error);
    showToast('Error al cargar estaciones', 'error');
    
    // Mantener opción de carga por si falla la API
    const select = document.getElementById('stopSelect');
    if (select) {
      select.innerHTML = '<option value="">Error al cargar estaciones</option>';
    }
  }
  showLoading(false);
}

// ========================================
// Event Listeners
// ========================================
function setupEventListeners() {
  console.log('Configurando event listeners...');
  
  // Búsqueda con debounce
  const searchBox = document.getElementById('searchBox');
  if (searchBox) {
    searchBox.addEventListener('input', (e) => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => performSearch(e.target.value), 300);
    });
    console.log('Search box listener configurado');
  } else {
    console.error('No se encontró searchBox');
  }
  
  // Selección de estación
  const stopSelect = document.getElementById('stopSelect');
  if (stopSelect) {
    stopSelect.addEventListener('change', onStopChange);
    console.log('Stop select listener configurado');
  } else {
    console.error('No se encontró stopSelect');
  }
  
  // Botón de actualización
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', refreshData);
    console.log('Refresh button listener configurado');
  } else {
    console.error('No se encontró refreshBtn');
  }
  
  // Auto-refresh toggle
  const autoRefreshToggle = document.getElementById('autoRefreshToggle');
  if (autoRefreshToggle) {
    autoRefreshToggle.addEventListener('click', toggleAutoRefresh);
    console.log('Auto-refresh toggle listener configurado');
  } else {
    console.error('No se encontró autoRefreshToggle');
  }
  
  // Cambio de fecha
  const dateSelect = document.getElementById('dateSelect');
  if (dateSelect) {
    dateSelect.addEventListener('change', () => {
      if (currentStop) refreshData();
    });
    console.log('Date select listener configurado');
  } else {
    console.error('No se encontró dateSelect');
  }
  
  // Paginación
  const prevPage = document.getElementById('prevPage');
  const nextPage = document.getElementById('nextPage');
  if (prevPage && nextPage) {
    prevPage.addEventListener('click', () => changePage(-1));
    nextPage.addEventListener('click', () => changePage(1));
    console.log('Pagination listeners configurados');
  } else {
    console.error('No se encontraron botones de paginación');
  }
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
    console.error('Search error:', error);
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
    
    // Actualizar información
    displayStopInfo(currentStop);
    
    // Actualizar mapa
    if (currentStop.stop_lat && currentStop.stop_lon) {
      updateMap(
        parseFloat(currentStop.stop_lat),
        parseFloat(currentStop.stop_lon),
        currentStop.stop_name
      );
    }
    
    // Cargar datos
    await refreshData();
    
  } catch (error) {
    console.error('Error loading stop:', error);
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
    // Cargar próximos trenes
    await loadUpcomingTrains(stopId);
    
    // Cargar horarios completos
    await loadSchedule(stopId, date);
    
  } catch (error) {
    console.error('Error refreshing data:', error);
    showToast('Error al actualizar datos', 'error');
  }
  
  showLoading(false);
}

// ========================================
// Cargar próximos trenes
// ========================================
async function loadUpcomingTrains(stopId) {
  try {
    const now = new Date();
    const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:00`;
    
    const response = await api(`/stops/${stopId}/upcoming?current_time=${currentTime}&limit=10`);
    const data = response.data;
    
    // Actualizar salidas
    displayDepartures(data.departures || []);
    
    // Actualizar llegadas
    displayArrivals(data.arrivals || []);
    
  } catch (error) {
    console.error('Error loading upcoming trains:', error);
    document.getElementById('departuresContent').innerHTML = 
      '<div class="text-center text-red-500 py-4">Error al cargar salidas</div>';
    document.getElementById('arrivalsContent').innerHTML = 
      '<div class="text-center text-red-500 py-4">Error al cargar llegadas</div>';
  }
}

function displayDepartures(departures) {
  const container = document.getElementById('departuresContent');
  const count = document.getElementById('departuresCount');
  count.textContent = departures.length;
  
  if (departures.length === 0) {
    container.innerHTML = '<div class="text-center text-slate-500 py-8">No hay salidas próximas</div>';
    return;
  }
  
  container.innerHTML = departures.map(train => {
    const isSoon = train.minutes_until <= 5;
    return `
      <div class="train-card bg-white dark:bg-slate-800 rounded-lg p-4 shadow-md">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-3">
            <span class="route-badge">${train.route_short_name || 'N/A'}</span>
            <div>
              <div class="font-semibold text-slate-800 dark:text-slate-200">
                ${train.trip_headsign || 'Destino no especificado'}
              </div>
              <div class="text-sm text-slate-500">Salida: ${train.scheduled_time}</div>
            </div>
          </div>
          <span class="time-badge ${isSoon ? 'soon' : ''}">${train.minutes_until} min</span>
        </div>
      </div>
    `;
  }).join('');
}

function displayArrivals(arrivals) {
  const container = document.getElementById('arrivalsContent');
  const count = document.getElementById('arrivalsCount');
  count.textContent = arrivals.length;
  
  if (arrivals.length === 0) {
    container.innerHTML = '<div class="text-center text-slate-500 py-8">No hay llegadas próximas</div>';
    return;
  }
  
  container.innerHTML = arrivals.map(train => {
    const isSoon = train.minutes_until <= 5;
    return `
      <div class="train-card bg-white dark:bg-slate-800 rounded-lg p-4 shadow-md">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-3">
            <span class="route-badge">${train.route_short_name || 'N/A'}</span>
            <div>
              <div class="font-semibold text-slate-800 dark:text-slate-200">
                ${train.trip_headsign || 'Origen no especificado'}
              </div>
              <div class="text-sm text-slate-500">Llegada: ${train.scheduled_time}</div>
            </div>
          </div>
          <span class="time-badge ${isSoon ? 'soon' : ''}">${train.minutes_until} min</span>
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
    
    displaySchedulePage();
    
  } catch (error) {
    console.error('Error loading schedule:', error);
    document.getElementById('scheduleContent').innerHTML = 
      '<div class="text-center text-red-500 py-4">Error al cargar horarios</div>';
  }
}

function displaySchedulePage() {
  const container = document.getElementById('scheduleContent');
  const allSchedule = window.allSchedule || [];
  
  if (allSchedule.length === 0) {
    container.innerHTML = '<div class="text-center text-slate-500 py-8">No hay horarios disponibles</div>';
    return;
  }
  
  const start = currentPage * pageSize;
  const end = start + pageSize;
  const page = allSchedule.slice(start, end);
  
  const table = `
    <table class="w-full">
      <thead class="bg-slate-100 dark:bg-slate-700">
        <tr>
          <th class="px-4 py-2 text-left">Hora</th>
          <th class="px-4 py-2 text-left">Línea</th>
          <th class="px-4 py-2 text-left">Viaje</th>
          <th class="px-4 py-2 text-left">Servicio</th>
        </tr>
      </thead>
      <tbody>
        ${page.map((row, i) => `
          <tr class="${i % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-750'}">
            <td class="px-4 py-2 font-semibold">${row.arrival_time || row.departure_time || '-'}</td>
            <td class="px-4 py-2">
              <span class="route-badge text-xs">${row.route_short_name || '-'}</span>
            </td>
            <td class="px-4 py-2 text-sm text-slate-600 dark:text-slate-400">${row.trip_id || '-'}</td>
            <td class="px-4 py-2 text-sm text-slate-600 dark:text-slate-400">${row.service_date || '-'}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <div class="mt-4 text-center text-sm text-slate-600 dark:text-slate-400">
      Mostrando ${start + 1} - ${Math.min(end, allSchedule.length)} de ${allSchedule.length} horarios
    </div>
  `;
  
  container.innerHTML = table;
}

function changePage(direction) {
  const allSchedule = window.allSchedule || [];
  const maxPage = Math.ceil(allSchedule.length / pageSize) - 1;
  
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
  
  // Cargar rutas disponibles
  loadRoutesForStop(stop.stop_id);
}

async function loadRoutesForStop(stopId) {
  try {
    const response = await api(`/schedule?stop_id=${stopId}&limit=100`);
    const schedule = response.data || [];
    
    // Extraer rutas únicas
    const uniqueRoutes = [...new Set(schedule.map(s => s.route_short_name || s.route_id).filter(Boolean))];
    
    const routesContent = document.getElementById('routesContent');
    if (uniqueRoutes.length === 0) {
      routesContent.innerHTML = '<div class="text-slate-500 text-sm">No hay rutas disponibles</div>';
      return;
    }
    
    routesContent.innerHTML = uniqueRoutes.map(route => `
      <span class="inline-block route-badge text-sm m-1">${route}</span>
    `).join('');
    
  } catch (error) {
    console.error('Error loading routes:', error);
  }
}

// ========================================
// Auto-refresh
// ========================================
function toggleAutoRefresh() {
  const icon = document.getElementById('autoRefreshIcon');
  
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
    icon.textContent = '⏸️';
    showToast('Auto-actualización desactivada', 'info');
  } else {
    autoRefreshInterval = setInterval(() => {
      if (currentStop) refreshData();
    }, 30000); // 30 segundos
    icon.textContent = '▶️';
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
