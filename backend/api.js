import axios from "axios";

export const BACKEND_URL = (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"))
  ? "http://localhost:8000"
  : (process.env.REACT_APP_BACKEND_URL || "https://anjana-wash-backend.onrender.com");
export const API = `${BACKEND_URL}/api`;

const axiosInstance = axios.create({
  baseURL: API,
  headers: {
    "Content-Type": "application/json"
  },
  timeout: 20000
});

// Automatic retry with backoff for poor network connection
const RETRY_LIMIT = 4;
const RETRY_DELAY = 1000;

axiosInstance.interceptors.response.use(undefined, async (err) => {
  const config = err.config;
  if (!config) return Promise.reject(err);
  
  config.__retryCount = config.__retryCount || 0;
  const isNetworkOrTimeout = !err.response || err.code === "ECONNABORTED" || err.message.includes("Network Error");
  
  if (isNetworkOrTimeout && config.__retryCount < RETRY_LIMIT) {
    config.__retryCount += 1;
    const delay = RETRY_DELAY * Math.pow(2, config.__retryCount);
    console.warn(`[Network Weak] Retrying ${config.url} (Attempt ${config.__retryCount} of ${RETRY_LIMIT}) in ${delay}ms...`);
    await new Promise(resolve => setTimeout(resolve, delay));
    return axiosInstance(config);
  }
  return Promise.reject(err);
});

const useBackend = !!process.env.REACT_APP_BACKEND_URL;

const compressImage = (base64Str, maxWidth = 1024, maxHeight = 1024, quality = 0.7) => {
  return new Promise((resolve) => {
    const img = new Image();
    img.src = base64Str;
    img.onload = () => {
      const canvas = document.createElement('canvas');
      let width = img.width;
      let height = img.height;

      if (width > height) {
        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }
      } else {
        if (height > maxHeight) {
          width = Math.round((width * maxHeight) / height);
          height = maxHeight;
        }
      }

      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);
      resolve(canvas.toDataURL('image/jpeg', quality));
    };
    img.onerror = () => {
      resolve(base64Str);
    };
  });
};

export const fileToBase64 = (file) =>
  new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = async () => {
      try {
        const compressed = await compressImage(r.result);
        resolve(compressed);
      } catch (err) {
        resolve(r.result);
      }
    };
    r.onerror = reject;
    r.readAsDataURL(file);
  });

// ---------- Static Categories ----------
const CATEGORIES = [
  {"id": "car", "label": "Car", "icon": "Car", "children": [
      {"id": "small_car", "label": "Small Car", "icon": "Car"},
      {"id": "xuv", "label": "Compact SUV", "icon": "Car"},
      {"id": "7seater", "label": "7-Seater", "icon": "Car"},
  ]},
  {"id": "auto", "label": "Auto", "icon": "Bus", "children": []},
  {"id": "ape_auto", "label": "Ape Auto", "icon": "Truck", "children": []},
  {"id": "tt", "label": "Tempo Traveller", "icon": "Bus", "children": []},
  {"id": "tractor", "label": "Tractor", "icon": "Tractor", "children": []},
  {"id": "tata_ace", "label": "Tata Ace", "icon": "Truck", "children": []},
  {"id": "bolero_leyland", "label": "Leyland / Bolero", "icon": "Truck", "children": []},
  {"id": "bike", "label": "Bike", "icon": "Bike", "children": []},
  {"id": "scooter", "label": "Scooter", "icon": "Bike", "children": []},
  {"id": "jcb", "label": "JCB", "icon": "Construction", "children": []},
  {"id": "others", "label": "Others", "icon": "Globe", "children": []},
];

const flattenLeafCategories = () => {
  const leaves = [];
  CATEGORIES.forEach(c => {
    if (c.children && c.children.length > 0) {
      c.children.forEach(ch => {
        leaves.push({
          id: ch.id,
          label: ch.label,
          parent_id: c.id,
          parent_label: c.label
        });
      });
    } else {
      leaves.push({
        id: c.id,
        label: c.label,
        parent_id: null,
        parent_label: null
      });
    }
  });
  return leaves;
};

const LEAF_BY_ID = {};
flattenLeafCategories().forEach(lf => {
  LEAF_BY_ID[lf.id] = lf;
});

const DEFAULT_SERVICE_PRICES = {
  "small_car": [
    ["Only Water", 100, "Water wash only"],
    ["Water + Dry", 150, "Water wash and drying"],
    ["Outside Wash", 250, "Exterior wash"],
    ["Body Wash", 350, "Full body wash"],
    ["Full Wash", 450, "Premium full wash"],
    ["Inside Vacuum", 100, "Interior vacuum cleaning"],
    ["Under Chassis Wash", 150, "Undercarriage cleaning"],
    ["Engine Wash", 100, "Engine bay cleaning"]
  ],
  "xuv": [
    ["Only Water", 150, "Water wash only"],
    ["Water + Dry", 200, "Water wash and drying"],
    ["Outside Wash", 300, "Exterior wash"],
    ["Body Wash", 450, "Full body wash"],
    ["Full Wash", 550, "Premium full wash"],
    ["Inside Vacuum", 150, "Interior vacuum cleaning"],
    ["Under Chassis Wash", 200, "Undercarriage cleaning"],
    ["Engine Wash", 150, "Engine bay cleaning"]
  ],
  "7seater": [
    ["Only Water", 180, "Water wash only"],
    ["Water + Dry", 250, "Water wash and drying"],
    ["Outside Wash", 350, "Exterior wash"],
    ["Body Wash", 550, "Full body wash"],
    ["Full Wash", 700, "Premium full wash"],
    ["Inside Vacuum", 200, "Interior vacuum cleaning"],
    ["Under Chassis Wash", 250, "Undercarriage cleaning"],
    ["Engine Wash", 200, "Engine bay cleaning"]
  ],
  "auto": [
    ["Water Full body", 200, "Complete body water wash"],
    ["Water only body", 150, "Body water wash only"],
    ["Water Engine", 150, "Engine water wash"],
    ["Body wash", 400, "Standard body wash"],
    ["Full wash", 500, "Premium full wash"],
    ["Full wash + Diesel spray", 550, "Full wash with diesel spray finish"]
  ],
  "ape_auto": [
    ["Water Full body", 300, "Complete body water wash"],
    ["Body wash", 500, "Standard body wash"],
    ["Full wash", 600, "Premium full wash"],
    ["Full wash + Diesel spray", 650, "Full wash with diesel spray finish"]
  ],
  "tt": [
    ["Only Body Water", 350, "Body water wash only"],
    ["Body wash", 600, "Standard body wash"],
    ["Full wash", 750, "Premium full wash"],
    ["Full wash + Diesel spray", 800, "Full wash with diesel spray finish"],
    ["Full wash + Grease", 800, "Full wash with grease service"],
    ["Under Chassis Wash", 400, "Undercarriage cleaning"],
    ["Under Chassis Wash + Grease", 500, "Undercarriage cleaning and grease service"],
    ["Only Inside Air + Mat clean", 400, "Interior air cleaning and mat wash"]
  ],
  "tata_ace": [
    ["Body wash", 500, "Standard body wash"],
    ["Full wash", 700, "Premium full wash"],
    ["Full wash + Grease", 750, "Full wash with grease service"],
    ["Under Chassis Wash", 350, "Undercarriage cleaning"],
    ["Under Chassis + Grease", 450, "Undercarriage cleaning and grease service"]
  ],
  "bolero_leyland": [
    ["Body wash", 600, "Standard body wash"],
    ["Full wash", 800, "Premium full wash"],
    ["Full wash + Grease", 850, "Full wash with grease service"],
    ["Full wash + Grease + Diesel spray", 900, "Full wash with grease and diesel spray finish"]
  ],
  "bike": [
    ["Water", 80, "Water wash only"],
    ["Foam Wash", 150, "Foam wash"],
    ["Foam Wash + Diesel Spray", 180, "Foam wash and diesel spray"],
    ["Chain Diesel Wash", 80, "Chain diesel wash"]
  ],
  "scooter": [
    ["Water", 80, "Water wash only"],
    ["Foam Wash", 120, "Foam wash"],
    ["Foam Wash + Diesel Spray", 150, "Foam wash and diesel spray"]
  ],
  "tractor": [
    ["Only Engine Water", 400, "Engine water wash only"],
    ["Only Engine Foam Wash", 700, "Engine foam wash only"],
    ["Only Engine Foam + Diesel Spray", 750, "Engine foam wash and diesel spray only"],
    ["Engine + Trolley Water", 700, "Engine and trolley water wash"],
    ["Engine + Trolley Full Wash + Diesel Spray", 1200, "Engine and trolley full wash with diesel spray"],
    ["Trolley Wash Foam + Diesel Spray", 700, "Trolley foam wash with diesel spray"],
    ["Engine Greasing", 250, "Engine greasing service"]
  ],
  "jcb": [
    ["Only Water", 1300, "Water wash only"],
    ["Full Wash with Foam and Diesel Spray", 2800, "Full wash with foam and diesel spray"],
    ["Greasing", 400, "Greasing service"]
  ],
  "others": [
    ["Others 200", 200, "Other custom service - ₹200"],
    ["Others 500", 500, "Other custom service - ₹500"],
    ["Others 1000", 1000, "Other custom service - ₹1000"],
    ["Others 1500", 1500, "Other custom service - ₹1500"],
    ["Others 2000", 2000, "Other custom service - ₹2000"],
    ["Others 2500", 2500, "Other custom service - ₹2500"],
    ["Others 3000", 3000, "Other custom service - ₹3000"]
  ]
};

// ---------- Database Initializer ----------
const formatDateToIstIso = (d) => {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });
  
  const parts = formatter.formatToParts(d);
  const getPart = (type) => parts.find(p => p.type === type).value;
  
  const yyyy = getPart("year");
  const mm = getPart("month");
  const dd = getPart("day");
  
  let hh = getPart("hour");
  if (hh === "24") hh = "00";
  
  const min = getPart("minute");
  const sec = getPart("second");
  
  const ms = String(d.getMilliseconds()).padStart(3, '0');
  
  return `${yyyy}-${mm}-${dd}T${hh}:${min}:${sec}.${ms}+05:30`;
};

const nowIstIso = () => formatDateToIstIso(new Date());

const todayKey = () => {
  const now = new Date();
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
  const parts = formatter.formatToParts(now);
  const getPart = (type) => parts.find(p => p.type === type).value;
  return `${getPart("year")}-${getPart("month")}-${getPart("day")}`;
};

const initDb = () => {
  const SERVICES_VERSION = "v7";
  const currentVersion = localStorage.getItem("anjana_services_version");
  if (currentVersion !== SERVICES_VERSION) {
    localStorage.removeItem("anjana_services");
    localStorage.setItem("anjana_services_version", SERVICES_VERSION);
  }

  const existingServices = localStorage.getItem("anjana_services");
  if (existingServices === null) {
    const services = [];
    Object.entries(DEFAULT_SERVICE_PRICES).forEach(([catId, list]) => {
      list.forEach(([name, price, desc]) => {
        services.push({
          id: Math.random().toString(36).substr(2, 9) + "-" + Date.now(),
          category_id: catId,
          name,
          price,
          description: desc,
          active: true
        });
      });
    });
    localStorage.setItem("anjana_services", JSON.stringify(services));
  }
  if (!localStorage.getItem("anjana_bookings")) {
    localStorage.setItem("anjana_bookings", JSON.stringify([]));
  }

  // Timezone format migration for existing bookings in localStorage
  const bookingsStr = localStorage.getItem("anjana_bookings");
  if (bookingsStr) {
    try {
      const bookings = JSON.parse(bookingsStr);
      let modified = false;
      const updatedBookings = bookings.map(b => {
        let updated = { ...b };
        if (updated.created_at && !updated.created_at.includes("+") && !updated.created_at.endsWith("Z")) {
          const d = new Date(updated.created_at + "Z");
          if (!isNaN(d.getTime())) {
            updated.created_at = formatDateToIstIso(d);
            modified = true;
          }
        }
        if (updated.completed_at && !updated.completed_at.includes("+") && !updated.completed_at.endsWith("Z")) {
          const d = new Date(updated.completed_at + "Z");
          if (!isNaN(d.getTime())) {
            updated.completed_at = formatDateToIstIso(d);
            modified = true;
          }
        }
        return updated;
      });
      if (modified) {
        localStorage.setItem("anjana_bookings", JSON.stringify(updatedBookings));
      }
    } catch (e) {
      console.error("Failed to migrate bookings:", e);
    }
  }

  if (!localStorage.getItem("anjana_config")) {
    localStorage.setItem("anjana_config", JSON.stringify({
      worker_pin: "1234",
      owner_pin: "9999"
    }));
  }
  if (!localStorage.getItem("anjana_counters")) {
    localStorage.setItem("anjana_counters", JSON.stringify({}));
  }
};


// ---------- Getters and Setters (Shared Database Sync) ----------
const BIN_URL = "https://extendsclass.com/api/json-storage/bin/aaeeccb";

let dbState = {
  bookings: [],
  services: [],
  config: { worker_pin: "1234", owner_pin: "9999" },
  counters: {}
};

const fetchRemoteState = async () => {
  let attempts = 0;
  const maxAttempts = 3;
  while (attempts < maxAttempts) {
    try {
      const res = await fetch(BIN_URL);
      if (!res.ok) throw new Error("Failed to load database");
      const data = await res.json();
      return data;
    } catch (e) {
      attempts++;
      if (attempts >= maxAttempts) {
        console.error("Database connection error, using local fallback:", e);
        return {
          bookings: JSON.parse(localStorage.getItem("anjana_bookings") || "[]"),
          services: JSON.parse(localStorage.getItem("anjana_services") || "[]"),
          config: JSON.parse(localStorage.getItem("anjana_config") || '{"worker_pin":"1234","owner_pin":"9999"}'),
          counters: JSON.parse(localStorage.getItem("anjana_counters") || "{}")
        };
      }
      const delay = 1000 * Math.pow(2, attempts);
      console.warn(`[Sync Weak] Retrying state load (${attempts}/${maxAttempts}) in ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
};

const saveRemoteState = async (state) => {
  let attempts = 0;
  const maxAttempts = 3;
  while (attempts < maxAttempts) {
    try {
      const res = await fetch(BIN_URL, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(state)
      });
      if (!res.ok) throw new Error("Failed to save database");
      return;
    } catch (e) {
      attempts++;
      if (attempts >= maxAttempts) {
        console.error("Database save error, saving locally:", e);
        localStorage.setItem("anjana_bookings", JSON.stringify(state.bookings));
        localStorage.setItem("anjana_services", JSON.stringify(state.services));
        localStorage.setItem("anjana_config", JSON.stringify(state.config));
        localStorage.setItem("anjana_counters", JSON.stringify(state.counters));
        return;
      }
      const delay = 1000 * Math.pow(2, attempts);
      console.warn(`[Sync Weak] Retrying state save (${attempts}/${maxAttempts}) in ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
};

const getServices = () => dbState.services;
const saveServices = (s) => { dbState.services = s; };

const getBookings = () => dbState.bookings;
const saveBookings = (b) => { dbState.bookings = b; };

const getConfig = () => dbState.config;
const saveConfig = (c) => { dbState.config = c; };

const getCounters = () => dbState.counters;
const saveCounters = (c) => { dbState.counters = c; };

// ---------- Token Generator ----------
const generateDailyToken = () => {
  const today = todayKey();
  const counters = getCounters();
  if (!counters[today]) {
    counters[today] = 0;
  }
  counters[today] += 1;
  saveCounters(counters);
  
  const seq = counters[today];
  const pad = String(seq).padStart(2, '0');
  return pad;
};

const mockError = (status, message) => {
  const err = new Error(message);
  err.response = {
    status,
    data: { detail: message }
  };
  return Promise.reject(err);
};

// ---------- Mock Request Handler ----------
const mockRequestOriginal = async (method, url, data, config) => {
  initDb();
  
  let path = url;
  if (path.startsWith(API)) {
    path = path.slice(API.length);
  }
  if (!path.startsWith("/")) {
    path = "/" + path;
  }
  
  // Parse query parameters
  let queryParams = {};
  if (path.includes("?")) {
    const parts = path.split("?");
    path = parts[0];
    const qStr = parts[1];
    qStr.split("&").forEach(p => {
      const kv = p.split("=");
      queryParams[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    });
  }

  // console.log(`[Mock API] ${method.toUpperCase()} ${path}`, { data, queryParams });

  // 1. GET /categories
  if (method === "get" && path === "/categories") {
    return { data: CATEGORIES };
  }

  // 2. GET /services/by-category/:category_id
  if (method === "get" && path.startsWith("/services/by-category/")) {
    const category_id = path.slice("/services/by-category/".length);
    if (!LEAF_BY_ID[category_id]) {
      return mockError(400, "Invalid category");
    }
    const services = getServices()
      .filter(s => s.category_id === category_id && s.active)
      .sort((a, b) => a.price - b.price);
    return { data: services };
  }

  // 3. GET /owner/services
  if (method === "get" && path === "/owner/services") {
    const services = getServices().sort((a, b) => {
      if (a.category_id !== b.category_id) {
        return a.category_id.localeCompare(b.category_id);
      }
      return a.price - b.price;
    });
    return { data: services };
  }

  // 4. POST /owner/services
  if (method === "post" && path === "/owner/services") {
    const { owner_pin, category_id, name, price, description } = data || {};
    const cfg = getConfig();
    if (cfg.owner_pin !== owner_pin) {
      return mockError(403, "Invalid owner PIN");
    }
    if (!LEAF_BY_ID[category_id]) {
      return mockError(400, "Invalid category");
    }
    if (!name || !name.trim() || !price || price <= 0) {
      return mockError(400, "Invalid service data");
    }
    const newService = {
      id: Math.random().toString(36).substr(2, 9) + "-" + Date.now(),
      category_id,
      name: name.trim(),
      price: parseInt(price, 10),
      description: (description || "").trim(),
      active: true
    };
    const services = getServices();
    services.push(newService);
    saveServices(services);
    return { data: newService };
  }

  // 5. PATCH /owner/services/:service_id
  if (method === "patch" && path.startsWith("/owner/services/")) {
    const service_id = path.slice("/owner/services/".length);
    const { owner_pin, name, price, description, active } = data || {};
    const cfg = getConfig();
    if (cfg.owner_pin !== owner_pin) {
      return mockError(403, "Invalid owner PIN");
    }
    const services = getServices();
    const svcIndex = services.findIndex(s => s.id === service_id);
    if (svcIndex === -1) {
      return mockError(404, "Service not found");
    }
    const updated = { ...services[svcIndex] };
    if (name !== undefined && name.trim()) updated.name = name.trim();
    if (price !== undefined && price > 0) updated.price = parseInt(price, 10);
    if (description !== undefined) updated.description = description.trim();
    if (active !== undefined) updated.active = !!active;

    services[svcIndex] = updated;
    saveServices(services);
    return { data: updated };
  }

  // 6. DELETE /owner/services/:service_id
  if (method === "delete" && path.startsWith("/owner/services/")) {
    const service_id = path.slice("/owner/services/".length);
    const reqData = data || (config && config.data) || {};
    const { owner_pin } = reqData;
    const cfg = getConfig();
    if (cfg.owner_pin !== owner_pin) {
      return mockError(403, "Invalid owner PIN");
    }
    const services = getServices();
    const filtered = services.filter(s => s.id !== service_id);
    if (services.length === filtered.length) {
      return mockError(404, "Service not found");
    }
    saveServices(filtered);
    return { data: { success: true } };
  }

  // 7. POST /bookings
  if (method === "post" && path === "/bookings") {
    const {
      customer_name,
      phone,
      vehicle_number,
      vehicle_photo,
      category_id,
      service_id,
      payment_method,
      payment_provider,
      worker_photo
    } = data || {};

    if (payment_method !== "cash" && payment_method !== "online") {
      return mockError(400, "Invalid payment method");
    }
    if (payment_method === "online" && payment_provider !== "phonepe" && payment_provider !== "gpay") {
      return mockError(400, "Invalid payment provider for online method");
    }
    if (!LEAF_BY_ID[category_id]) {
      return mockError(400, "Invalid category");
    }
    const services = getServices();
    const service = services.find(s => s.id === service_id && s.active);
    if (!service) {
      return mockError(400, "Invalid or inactive service");
    }
    if (service.category_id !== category_id) {
      return mockError(400, "Service does not belong to the selected category");
    }
    const leaf = LEAF_BY_ID[category_id];
    const token = payment_method === "online" ? "Pending Payment" : generateDailyToken();
    const newBooking = {
      id: Math.random().toString(36).substr(2, 9) + "-" + Date.now(),
      token,
      customer_name: (customer_name || "").trim(),
      phone: (phone || "").trim(),
      vehicle_number: (vehicle_number || "").trim().toUpperCase(),
      vehicle_photo,
      category_id,
      category_label: leaf.label,
      parent_category_id: leaf.parent_id,
      parent_category_label: leaf.parent_label,
      service_id: service.id,
      service_name: service.name,
      price: service.price,
      payment_method,
      payment_provider: payment_method === "online" ? payment_provider : null,
      payment_status: "pending",
      status: "queued",
      worker_photo: worker_photo || null,
      created_at: nowIstIso(),
      completed_at: null
    };

    const bookings = getBookings();
    bookings.push(newBooking);
    try {
      saveBookings(bookings);
    } catch (e) {
      return mockError(400, e.message || "Failed to save booking data due to storage limit.");
    }
    return { data: newBooking };
  }

  // 8. GET /bookings/queue
  if (method === "get" && path === "/bookings/queue") {
    const bookings = getBookings();
    const queue = bookings
      .filter(b => b.status === "queued" && (b.payment_method === "cash" || b.payment_status === "paid"))
      .sort((a, b) => a.created_at.localeCompare(b.created_at));
    return { data: queue };
  }

  // 9. GET /bookings
  if (method === "get" && path === "/bookings") {
    const date = queryParams.date || (config && config.params && config.params.date);
    let bookings = getBookings();
    if (date) {
      bookings = bookings.filter(b => b.created_at.startsWith(date));
    }
    bookings.sort((a, b) => b.created_at.localeCompare(a.created_at));
    return { data: bookings };
  }

  // 12. GET /bookings/stats/today
  if (method === "get" && path === "/bookings/stats/today") {
    const today = todayKey();
    const bookings = getBookings();
    const items = bookings.filter(b => b.created_at.startsWith(today));
    
    const paid = items.filter(b => b.payment_status === "paid");
    const cash = paid.filter(b => b.payment_method === "cash");
    const online = paid.filter(b => b.payment_method === "online");
    const completed = items.filter(b => b.status === "completed");

    const stats = {
      date: today,
      total_bookings: items.length,
      completed: completed.length,
      pending: items.filter(b => b.status === "queued").length,
      cash_count: cash.length,
      online_count: online.length,
      cash_amount: cash.reduce((sum, b) => sum + (Number(b.price) || 0), 0),
      online_amount: online.reduce((sum, b) => sum + (Number(b.price) || 0), 0),
      total_earnings: paid.reduce((sum, b) => sum + (Number(b.price) || 0), 0)
    };
    return { data: stats };
  }

  // 10. GET /bookings/:booking_id
  if (method === "get" && path.startsWith("/bookings/") && path !== "/bookings/queue" && path !== "/bookings/stats/today") {
    const booking_id = path.slice("/bookings/".length);
    const bookings = getBookings();
    const booking = bookings.find(b => b.id === booking_id);
    if (!booking) {
      return mockError(404, "Booking not found");
    }
    return { data: booking };
  }

  // 20. GET /bookings/latest-id
  if (method === "get" && path === "/bookings/latest-id") {
    const bookings = getBookings().filter(
      b => b.status === "queued" && (b.payment_method === "cash" || b.payment_status === "paid")
    );
    bookings.sort((x, y) => y.created_at.localeCompare(x.created_at));
    return { data: { latest_id: bookings[0]?.id || "" } };
  }

  // 19. GET /bookings/:booking_id/photo
  if (method === "get" && path.startsWith("/bookings/") && path.endsWith("/photo")) {
    const parts = path.split("/");
    const booking_id = parts[2];
    const bookings = getBookings();
    const booking = bookings.find(b => b.id === booking_id);
    if (!booking) {
      return mockError(404, "Booking not found");
    }
    return { data: { vehicle_photo: booking.vehicle_photo, worker_photo: booking.worker_photo } };
  }

  // 11. POST /bookings/:booking_id/complete
  if (method === "post" && path.startsWith("/bookings/") && path.endsWith("/complete")) {
    const parts = path.split("/");
    const booking_id = parts[2];
    const { worker_photo } = data || {};
    const bookings = getBookings();
    const idx = bookings.findIndex(b => b.id === booking_id);
    if (idx === -1) {
      return mockError(404, "Booking not found");
    }
    const b = bookings[idx];
    if (b.status === "completed") {
      return mockError(400, "Already completed");
    }

    const updated = {
      ...b,
      status: "completed",
      completed_at: nowIstIso()
    };
    if (b.payment_method === "cash") {
      updated.worker_photo = worker_photo || b.worker_photo;
      updated.payment_status = "paid";
    }
    if (worker_photo && b.payment_method !== "cash") {
      updated.worker_photo = worker_photo;
    }

    bookings[idx] = updated;
    saveBookings(bookings);
    return { data: updated };
  }

  // 13. POST /auth/verify-pin
  if (method === "post" && path === "/auth/verify-pin") {
    const { role, pin } = data || {};
    const cfg = getConfig();
    const key = `${role}_pin`;
    if (!cfg[key]) {
      return mockError(400, "Invalid role");
    }
    return { data: { success: cfg[key] === pin } };
  }

  // 14. POST /auth/update-pin
  if (method === "post" && path === "/auth/update-pin") {
    const { owner_pin, role, new_pin } = data || {};
    const cfg = getConfig();
    if (cfg.owner_pin !== owner_pin) {
      return mockError(403, "Invalid owner PIN");
    }
    if (role !== "worker" && role !== "owner") {
      return mockError(400, "Invalid role");
    }
    if (!new_pin || !/^\d+$/.test(new_pin) || new_pin.length < 4 || new_pin.length > 6) {
      return mockError(400, "PIN must be 4-6 digits");
    }
    cfg[`${role}_pin`] = new_pin;
    saveConfig(cfg);
    return { data: { success: true } };
  }

  // 15. POST /payment/phonepe/initiate
  if (method === "post" && path === "/payment/phonepe/initiate") {
    const { booking_id } = data || {};
    const bookings = getBookings();
    const idx = bookings.findIndex(b => b.id === booking_id);
    if (idx === -1) {
      return mockError(404, "Booking not found");
    }
    bookings[idx].payment_provider = "phonepe";
    saveBookings(bookings);

    return {
      data: {
        success: true,
        checkout_url: `/phonepe-mock?booking_id=${booking_id}`,
        merchant_order_id: booking_id,
        amount: bookings[idx].price,
        provider: "phonepe",
        mocked: true
      }
    };
  }

  // 16. POST /payment/phonepe/callback
  if (method === "post" && path === "/payment/phonepe/callback") {
    const { booking_id } = data || {};
    const bookings = getBookings();
    const idx = bookings.findIndex(b => b.id === booking_id);
    if (idx === -1) {
      return mockError(404, "Booking not found");
    }
    if (bookings[idx].token === "Pending Payment") {
      bookings[idx].token = generateDailyToken();
    }
    bookings[idx].payment_status = "paid";
    saveBookings(bookings);
    return { data: { success: true, booking: bookings[idx] } };
  }

  // 17. POST /payment/gpay/initiate
  if (method === "post" && path === "/payment/gpay/initiate") {
    const { booking_id } = data || {};
    const bookings = getBookings();
    const idx = bookings.findIndex(b => b.id === booking_id);
    if (idx === -1) {
      return mockError(404, "Booking not found");
    }
    bookings[idx].payment_provider = "gpay";
    saveBookings(bookings);

    return {
      data: {
        success: true,
        checkout_url: `/gpay-mock?booking_id=${booking_id}`,
        merchant_order_id: booking_id,
        amount: bookings[idx].price,
        provider: "gpay",
        mocked: true
      }
    };
  }

  // 18. POST /payment/gpay/callback
  if (method === "post" && path === "/payment/gpay/callback") {
    const { booking_id } = data || {};
    const bookings = getBookings();
    const idx = bookings.findIndex(b => b.id === booking_id);
    if (idx === -1) {
      return mockError(404, "Booking not found");
    }
    if (bookings[idx].token === "Pending Payment") {
      bookings[idx].token = generateDailyToken();
    }
    bookings[idx].payment_status = "paid";
    saveBookings(bookings);
    return { data: { success: true, booking: bookings[idx] } };
  }

  return mockError(404, `Endpoint ${method.toUpperCase()} ${path} not found in mock adapter`);
};

const mockRequest = async (method, url, data, config) => {
  const remote = await fetchRemoteState();
  dbState = remote;
  initDb();
  
  const result = await mockRequestOriginal(method, url, data, config);
  
  if (method !== "get") {
    await saveRemoteState(dbState);
  }
  
  return result;
};

// ---------- API Axios-Interface Wrapper ----------
export const api = {
  get: (url, config) => {
    if (useBackend) return axiosInstance.get(url, config);
    return mockRequest("get", url, null, config);
  },
  post: (url, data, config) => {
    if (useBackend) return axiosInstance.post(url, data, config);
    return mockRequest("post", url, data, config);
  },
  patch: (url, data, config) => {
    if (useBackend) return axiosInstance.patch(url, data, config);
    return mockRequest("patch", url, data, config);
  },
  delete: (url, config) => {
    if (useBackend) return axiosInstance.delete(url, config);
    return mockRequest("delete", url, null, config);
  }
};
