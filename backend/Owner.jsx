import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { IndianRupee, Banknote, Smartphone, CircleCheck, Settings2, KeyRound, X, TrendingUp, ListPlus, Pencil, Trash2, Plus, Download, FolderArchive } from "lucide-react";
import { toast } from "sonner";
import { formatIstTime } from "@/lib/utils";

const getPast15Days = () => {
  const list = [];
  const now = new Date();
  const istTime = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
  for (let i = 0; i < 15; i++) {
    const d = new Date(istTime);
    d.setDate(d.getDate() - i);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    list.push(`${yyyy}-${mm}-${dd}`);
  }
  return list;
};

export default function Owner() {
  const [stats, setStats] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [showPinMgr, setShowPinMgr] = useState(false);
  const [showSvcMgr, setShowSvcMgr] = useState(false);
  const [showArchiveMgr, setShowArchiveMgr] = useState(false);
  const [selectedDate, setSelectedDate] = useState("all");

  const load = useCallback(async () => {
    const [a, b] = await Promise.all([api.get("/bookings/stats/today"), api.get("/bookings")]);
    setStats(a.data); setBookings(b.data);
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, [load]);

  if (!stats) return <div className="p-10 text-center text-muted-foreground">Loading…</div>;

  const chartData = [
    { name: "Cash", value: stats?.cash_amount || 0, fill: "hsl(var(--accent))" },
    { name: "Online", value: stats?.online_amount || 0, fill: "hsl(var(--primary))" },
  ];
  const past15Days = getPast15Days();
  const completed = bookings.filter((b) => {
    if (b.status !== "completed") return false;
    const createdDate = b.created_at.split("T")[0];
    if (!past15Days.includes(createdDate)) return false;
    if (selectedDate === "all") return true;
    return createdDate === selectedDate;
  });

  return (
    <div className="mx-auto max-w-6xl px-6 py-8" data-testid="owner-dashboard">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <div className="label-caps">Control Room · {stats.date}</div>
          <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight mt-1">Owner Dashboard</h1>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowSvcMgr(true)}
            data-testid="open-service-manager"
            className="h-11 px-5 bg-card border border-border rounded-full font-display font-bold flex items-center gap-2 elev-2 hover:elev-3 transition-all"
          >
            <ListPlus className="h-4 w-4" strokeWidth={2.5} /> Manage Services
          </button>
          <button
            onClick={() => setShowArchiveMgr(true)}
            className="h-11 px-5 bg-card border border-border rounded-full font-display font-bold flex items-center gap-2 elev-2 hover:elev-3 transition-all"
          >
            <FolderArchive className="h-4 w-4" strokeWidth={2.5} /> Data Archive
          </button>
          <button
            onClick={() => setShowPinMgr(true)}
            data-testid="open-pin-manager"
            className="h-11 px-5 bg-card border border-border rounded-full font-display font-bold flex items-center gap-2 elev-2 hover:elev-3 transition-all"
          >
            <Settings2 className="h-4 w-4" strokeWidth={2.5} /> Change PINs
          </button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat testid="stat-earnings" icon={IndianRupee} label="Today's Earnings" value={`₹${stats.total_earnings}`} highlight />
        <Stat testid="stat-cash" icon={Banknote} label="Cash" value={`₹${stats.cash_amount}`} sub={`${stats.cash_count} txn`} />
        <Stat testid="stat-online" icon={Smartphone} label="Online" value={`₹${stats.online_amount}`} sub={`${stats.online_count} txn`} />
        <Stat testid="stat-completed" icon={CircleCheck} label="Completed" value={stats.completed} sub={`${stats.pending} pending`} />
      </div>

      {/* Chart + total */}
      <div className="mt-6 grid md:grid-cols-3 gap-4">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-[18px] p-5 md:col-span-2 elev-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="label-caps">Payment Split</div>
              <div className="font-display font-bold text-lg">Cash vs Online</div>
            </div>
            <div className="chip bg-success/10 text-foreground border-success/30 flex items-center gap-1" style={{ borderColor: "hsl(var(--success) / 0.3)" }}>
              <TrendingUp className="h-3 w-3" strokeWidth={2.5} /> Live
            </div>
          </div>
          <div className="h-56 mt-3">
            <ResponsiveContainer>
              <BarChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
                <XAxis dataKey="name" tick={{ fontFamily: "Outfit", fontWeight: 700, fill: "hsl(var(--muted-foreground))" }} axisLine={{ stroke: "hsl(var(--border))" }} tickLine={false} />
                <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: "hsl(var(--muted))" }}
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12, fontFamily: "IBM Plex Sans" }}
                />
                <Bar dataKey="value" radius={[10, 10, 0, 0]}>
                  {chartData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="relative rounded-[18px] overflow-hidden p-6 bg-secondary text-secondary-foreground flex flex-col justify-between elev-3 noise">
          <div className="absolute -top-20 -right-20 h-52 w-52 rounded-full bg-primary/40 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 h-52 w-52 rounded-full bg-accent/30 blur-3xl" />
          <div className="relative">
            <div className="label-caps text-accent">Total Bookings</div>
            <div className="font-display font-black text-6xl tracking-tighter mt-1">{stats.total_bookings}</div>
          </div>
          <div className="relative text-sm opacity-80">Today's footfall at Anjana Wash.</div>
        </motion.div>
      </div>

      {/* Recent completions */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-3">
          <div>
            <div className="label-caps">Recent Completions</div>
            <div className="font-display font-bold text-xl">Log Viewer</div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="h-10 px-4 bg-card border border-border rounded-full font-display font-bold text-sm outline-none cursor-pointer hover:bg-muted transition-all"
            >
              <option value="all">All 15 Days</option>
              {getPast15Days().map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <div className="text-xs text-muted-foreground">{completed.length} entries</div>
          </div>
        </div>
        <div className="grid gap-3">
          {completed.length === 0 && (
            <div className="bg-card border border-dashed border-border rounded-[18px] p-10 text-center text-muted-foreground">No completions in the last 15 days.</div>
          )}
          {completed.slice(0, 100).map((b, i) => (
            <motion.div
              key={b.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.01, duration: 0.35 }}
              className="bg-card border border-border rounded-[16px] p-3 flex flex-wrap items-center gap-4 elev-2"
              data-testid={`completion-${b.token}`}
            >
              <img src={b.vehicle_photo} alt="" className="h-16 w-24 object-cover rounded-[10px] border border-border flex-shrink-0" />
              <div className="flex-1 min-w-[180px]">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-display font-black bg-secondary text-secondary-foreground px-2 py-0.5 rounded-[8px] text-xs">{b.token}</span>
                  <span className="font-display font-bold">{b.customer_name}</span>
                </div>
                <div className="font-mono text-xs text-muted-foreground mt-0.5">{b.vehicle_number} · <span className="text-foreground/90 font-bold">{b.phone}</span> · {b.service_name} · ₹{b.price}</div>
                <div className="text-xs text-muted-foreground">Completed {fmt(b.completed_at)}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`chip ${b.payment_method === "cash" ? "bg-accent/15 border-accent/30" : "bg-primary/10 text-primary border-primary/20"}`}>
                  {b.payment_method === "cash" ? "cash" : (b.payment_provider === "gpay" ? "gpay" : "phonepe")}
                </span>
                {b.worker_photo && (
                  <img src={b.worker_photo} alt="" className="h-14 w-14 object-cover rounded-[10px] border border-border" title="Worker photo" />
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      <AnimatePresence>
        {showPinMgr && <PinManager onClose={() => setShowPinMgr(false)} />}
        {showSvcMgr && <ServiceManager onClose={() => setShowSvcMgr(false)} />}
        {showArchiveMgr && <ArchiveManager onClose={() => setShowArchiveMgr(false)} />}
      </AnimatePresence>
    </div>
  );
}

function Stat({ icon: Icon, label, value, sub, highlight, testid }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative rounded-[16px] p-4 border overflow-hidden ${highlight ? "bg-secondary text-secondary-foreground border-secondary elev-3" : "bg-card border-border elev-2"}`}
      data-testid={testid}
    >
      {highlight && <div className="absolute -top-10 -right-10 h-32 w-32 rounded-full bg-accent/30 blur-2xl" />}
      <div className="relative flex items-center justify-between">
        <div className="label-caps" style={highlight ? { color: "hsl(var(--accent))" } : {}}>{label}</div>
        <div className={`h-8 w-8 rounded-[10px] grid place-items-center ${highlight ? "bg-accent text-accent-foreground" : "bg-muted text-foreground"}`}>
          <Icon className="h-4 w-4" strokeWidth={2.5} />
        </div>
      </div>
      <div className="relative font-display font-black text-3xl tracking-tighter mt-2">{value}</div>
      {sub && <div className={`relative text-xs mt-0.5 ${highlight ? "opacity-80" : "text-muted-foreground"}`}>{sub}</div>}
    </motion.div>
  );
}

function fmt(iso) {
  return formatIstTime(iso);
}

function PinManager({ onClose }) {
  const [ownerPin, setOwnerPin] = useState("");
  const [role, setRole] = useState("worker");
  const [newPin, setNewPin] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!/^\d{4,6}$/.test(newPin)) { toast.error("PIN must be 4-6 digits"); return; }
    if (!/^\d{4,6}$/.test(ownerPin)) { toast.error("Enter current owner PIN"); return; }
    setBusy(true);
    try {
      await api.post("/auth/update-pin", { owner_pin: ownerPin, role, new_pin: newPin });
      toast.success(`${role} PIN updated`);
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update");
    } finally { setBusy(false); }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/60 backdrop-blur-sm grid place-items-center p-6 z-50" data-testid="pin-manager">
      <motion.div initial={{ scale: 0.94, y: 10, opacity: 0 }} animate={{ scale: 1, y: 0, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }} transition={{ duration: 0.25 }} className="bg-card border border-border rounded-[22px] w-full max-w-md p-6 elev-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-[12px] bg-primary/10 text-primary grid place-items-center">
              <KeyRound className="h-5 w-5" strokeWidth={2.5} />
            </div>
            <div>
              <div className="label-caps">Manage PINs</div>
              <h2 className="font-display font-black text-xl tracking-tight">Change Access PIN</h2>
            </div>
          </div>
          <button onClick={onClose} className="h-9 w-9 rounded-full grid place-items-center hover:bg-muted"><X className="h-4 w-4" strokeWidth={2.5} /></button>
        </div>

        <div className="mt-5 space-y-4">
          <div>
            <div className="label-caps mb-2">Current Owner PIN</div>
            <input data-testid="pin-mgr-owner" inputMode="numeric" value={ownerPin} onChange={(e) => setOwnerPin(e.target.value.replace(/\D/g, "").slice(0, 6))} className="input-field font-mono" />
          </div>
          <div>
            <div className="label-caps mb-2">Change PIN For</div>
            <div className="grid grid-cols-2 gap-2 bg-muted p-1 rounded-full">
              {["worker", "owner"].map((r) => (
                <button
                  key={r}
                  onClick={() => setRole(r)}
                  data-testid={`role-${r}`}
                  className={`h-10 rounded-full font-display font-bold capitalize text-sm transition-all ${role === r ? "bg-card elev-1" : "text-muted-foreground"}`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="label-caps mb-2">New PIN (4-6 digits)</div>
            <input data-testid="pin-mgr-new" inputMode="numeric" value={newPin} onChange={(e) => setNewPin(e.target.value.replace(/\D/g, "").slice(0, 6))} className="input-field font-mono" />
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3">
          <button onClick={onClose} className="h-11 bg-card border border-border rounded-full font-display font-bold">Cancel</button>
          <button onClick={save} disabled={busy} data-testid="pin-mgr-save" className="h-11 bg-primary text-primary-foreground rounded-full font-display font-bold brand-glow disabled:opacity-50">
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}


function ServiceManager({ onClose }) {
  const [ownerPin, setOwnerPin] = useState("");
  const [authed, setAuthed] = useState(false);
  const [services, setServices] = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeCat, setActiveCat] = useState(null);
  const [editing, setEditing] = useState(null); // service object or null
  const [adding, setAdding] = useState(false);

  const refresh = async () => {
    const [s, c] = await Promise.all([api.get("/owner/services"), api.get("/categories")]);
    setServices(s.data); setCategories(c.data);
    if (!activeCat) {
      // pick first leaf
      const flat = [];
      c.data.forEach((cc) => {
        if (cc.children?.length) cc.children.forEach((ch) => flat.push({ id: ch.id, label: `${cc.label} · ${ch.label}` }));
        else flat.push({ id: cc.id, label: cc.label });
      });
      setActiveCat(flat[0]?.id || null);
    }
  };

  const authenticate = async () => {
    if (!/^\d{4,6}$/.test(ownerPin)) { toast.error("Enter owner PIN"); return; }
    try {
      const { data } = await api.post("/auth/verify-pin", { role: "owner", pin: ownerPin });
      if (!data.success) { toast.error("Wrong owner PIN"); return; }
      setAuthed(true);
      await refresh();
    } catch { toast.error("Failed to verify"); }
  };

  const remove = async (svc) => {
    if (!window.confirm(`Delete "${svc.name}"?`)) return;
    try {
      await api.delete(`/owner/services/${svc.id}`, { data: { owner_pin: ownerPin } });
      toast.success("Deleted"); refresh();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  const flatCats = [];
  categories.forEach((cc) => {
    if (cc.children?.length) cc.children.forEach((ch) => flatCats.push({ id: ch.id, label: `${cc.label} · ${ch.label}` }));
    else flatCats.push({ id: cc.id, label: cc.label });
  });

  const visible = services.filter((s) => s.category_id === activeCat);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/60 backdrop-blur-sm grid place-items-center p-4 sm:p-6 z-50" data-testid="service-manager">
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} transition={{ duration: 0.25 }} className="bg-card border border-border rounded-[22px] w-full max-w-3xl max-h-[88vh] overflow-hidden elev-3 flex flex-col">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-[12px] bg-primary/10 text-primary grid place-items-center">
              <ListPlus className="h-5 w-5" strokeWidth={2.5} />
            </div>
            <div>
              <div className="label-caps">Owner · Services</div>
              <h2 className="font-display font-black text-xl tracking-tight">Manage services & prices</h2>
            </div>
          </div>
          <button onClick={onClose} className="h-9 w-9 rounded-full grid place-items-center hover:bg-muted"><X className="h-4 w-4" strokeWidth={2.5} /></button>
        </div>

        {!authed ? (
          <div className="p-8">
            <div className="label-caps mb-2">Enter Owner PIN to manage services</div>
            <div className="flex gap-2">
              <input data-testid="svc-mgr-pin" inputMode="numeric" value={ownerPin} onChange={(e) => setOwnerPin(e.target.value.replace(/\D/g, "").slice(0, 6))} className="input-field font-mono flex-1" placeholder="••••" />
              <button onClick={authenticate} data-testid="svc-mgr-auth" className="h-12 px-6 bg-primary text-primary-foreground rounded-full font-display font-bold brand-glow">Unlock</button>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-hidden grid grid-cols-1 sm:grid-cols-[200px_1fr]">
            <aside className="border-r border-border p-3 overflow-y-auto scrollbar-thin">
              <div className="label-caps mb-2 px-2">Categories</div>
              <div className="grid gap-1">
                {flatCats.map((c) => (
                  <button
                    key={c.id}
                    data-testid={`svc-cat-${c.id}`}
                    onClick={() => setActiveCat(c.id)}
                    className={`text-left px-3 py-2 rounded-[10px] text-sm font-semibold transition-colors ${activeCat === c.id ? "bg-secondary text-secondary-foreground" : "hover:bg-muted"}`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </aside>
            <main className="p-5 overflow-y-auto scrollbar-thin">
              <div className="flex items-center justify-between mb-4">
                <div className="font-display font-bold text-lg">{flatCats.find((c) => c.id === activeCat)?.label || ""}</div>
                <button onClick={() => setAdding(true)} data-testid="svc-add" className="chip bg-primary/10 text-primary border-primary/20 hover:bg-primary/15">
                  <Plus className="h-3 w-3" strokeWidth={2.5} /> Add service
                </button>
              </div>

              {adding && <ServiceForm initial={null} onCancel={() => setAdding(false)} onSave={async (form) => {
                try {
                  await api.post("/owner/services", { owner_pin: ownerPin, category_id: activeCat, ...form });
                  toast.success("Added"); setAdding(false); refresh();
                } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
              }} />}

              {visible.length === 0 && !adding && (
                <div className="text-sm text-muted-foreground py-8 text-center bg-muted/40 rounded-[14px]">No services for this category yet. Click "Add service".</div>
              )}

              <div className="grid gap-2 mt-3">
                {visible.map((s) => (
                  editing?.id === s.id ? (
                    <ServiceForm key={s.id} initial={s} onCancel={() => setEditing(null)} onSave={async (form) => {
                      try {
                        await api.patch(`/owner/services/${s.id}`, { owner_pin: ownerPin, ...form });
                        toast.success("Updated"); setEditing(null); refresh();
                      } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
                    }} />
                  ) : (
                    <div key={s.id} data-testid={`svc-row-${s.id}`} className={`bg-card border rounded-[12px] p-3 flex items-center gap-3 ${s.active ? "border-border" : "border-dashed border-border opacity-60"}`}>
                      <div className="flex-1 min-w-0">
                        <div className="font-display font-bold">{s.name} {!s.active && <span className="chip bg-muted ml-1 text-[9px]">inactive</span>}</div>
                        {s.description && <div className="text-xs text-muted-foreground">{s.description}</div>}
                      </div>
                      <div className="font-display font-black text-xl tracking-tighter">₹{s.price}</div>
                      <button onClick={() => setEditing(s)} data-testid={`svc-edit-${s.id}`} className="h-8 w-8 rounded-full grid place-items-center hover:bg-muted"><Pencil className="h-4 w-4" strokeWidth={2.5} /></button>
                      <button onClick={() => remove(s)} data-testid={`svc-del-${s.id}`} className="h-8 w-8 rounded-full grid place-items-center hover:bg-destructive hover:text-destructive-foreground"><Trash2 className="h-4 w-4" strokeWidth={2.5} /></button>
                    </div>
                  )
                ))}
              </div>
            </main>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

function ServiceForm({ initial, onCancel, onSave }) {
  const [name, setName] = useState(initial?.name || "");
  const [price, setPrice] = useState(initial?.price ?? "");
  const [description, setDescription] = useState(initial?.description || "");
  const [active, setActive] = useState(initial?.active ?? true);

  const submit = (e) => {
    e.preventDefault();
    if (!name.trim()) { toast.error("Name required"); return; }
    const p = parseInt(price, 10);
    if (!p || p <= 0) { toast.error("Price must be > 0"); return; }
    onSave(initial ? { name, price: p, description, active } : { name, price: p, description });
  };

  return (
    <form onSubmit={submit} className="bg-muted/40 border border-border rounded-[12px] p-3 grid gap-2 sm:grid-cols-[1fr_120px_auto]">
      <input data-testid="svc-form-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Service name" className="input-field h-10" />
      <input data-testid="svc-form-price" type="number" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="₹" className="input-field h-10 font-mono" />
      <div className="flex gap-2">
        <button type="button" onClick={onCancel} className="h-10 px-3 rounded-full border border-border font-bold text-sm">Cancel</button>
        <button type="submit" data-testid="svc-form-save" className="h-10 px-4 rounded-full bg-primary text-primary-foreground font-bold text-sm">{initial ? "Update" : "Add"}</button>
      </div>
      <input data-testid="svc-form-desc" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optional)" className="input-field h-10 sm:col-span-3" />
      {initial && (
        <label className="flex items-center gap-2 text-xs sm:col-span-3">
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> Active (visible to customers)
        </label>
      )}
    </form>
  );
}

function ArchiveManager({ onClose }) {
  const [ownerPin, setOwnerPin] = useState("");
  const [authed, setAuthed] = useState(false);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const refreshStatus = async () => {
    try {
      const { data } = await api.get("/bookings/archive/status");
      setStatus(data);
    } catch {
      toast.error("Failed to load archive status");
    }
  };

  const authenticate = async () => {
    if (!/^\d{4,6}$/.test(ownerPin)) { toast.error("Enter owner PIN"); return; }
    try {
      const { data } = await api.post("/auth/verify-pin", { role: "owner", pin: ownerPin });
      if (!data.success) { toast.error("Wrong owner PIN"); return; }
      setAuthed(true);
      await refreshStatus();
    } catch { toast.error("Failed to verify PIN"); }
  };

  const download = () => {
    const url = `${api.defaults.baseURL}/bookings/archive/download?owner_pin=${ownerPin}`;
    window.open(url, "_blank");
    toast.success("Download started");
  };

  const clearOld = async () => {
    if (!window.confirm("WARNING: Are you sure you want to delete all bookings older than 15 days? Make sure you have downloaded the archive first! This action CANNOT be undone.")) return;
    setBusy(true);
    try {
      const { data } = await api.post("/bookings/archive/clear", { owner_pin: ownerPin });
      toast.success(`Successfully cleared ${data.deleted_count} old bookings`);
      refreshStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to clear database");
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/60 backdrop-blur-sm grid place-items-center p-6 z-50">
      <motion.div initial={{ scale: 0.94, y: 10, opacity: 0 }} animate={{ scale: 1, y: 0, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }} transition={{ duration: 0.25 }} className="bg-card border border-border rounded-[22px] w-full max-w-md p-6 elev-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-[12px] bg-primary/10 text-primary grid place-items-center">
              <FolderArchive className="h-5 w-5" strokeWidth={2.5} />
            </div>
            <div>
              <div className="label-caps">Data Archive</div>
              <h2 className="font-display font-black text-xl tracking-tight">Archive & Clear Logs</h2>
            </div>
          </div>
          <button onClick={onClose} className="h-9 w-9 rounded-full grid place-items-center hover:bg-muted"><X className="h-4 w-4" strokeWidth={2.5} /></button>
        </div>

        {!authed ? (
          <div className="mt-5 space-y-4">
            <div>
              <div className="label-caps mb-2">Enter Owner PIN to unlock archives</div>
              <div className="flex gap-2">
                <input type="password" inputMode="numeric" value={ownerPin} onChange={(e) => setOwnerPin(e.target.value.replace(/\D/g, "").slice(0, 6))} className="input-field font-mono flex-1" placeholder="••••" />
                <button onClick={authenticate} className="h-12 px-6 bg-primary text-primary-foreground rounded-full font-display font-bold brand-glow">Unlock</button>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            {status ? (
              <div className="bg-muted/40 border border-border rounded-[14px] p-4 text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Bookings in DB:</span>
                  <span className="font-bold">{status.total_bookings}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Bookings older than 15 days:</span>
                  <span className="font-bold text-accent">{status.old_bookings}</span>
                </div>
              </div>
            ) : (
              <div className="text-center text-muted-foreground text-sm py-4">Loading stats...</div>
            )}

            <div className="grid gap-3 mt-4">
              <button
                onClick={download}
                disabled={!status || status.old_bookings === 0}
                className="w-full h-12 bg-primary text-primary-foreground rounded-full font-display font-bold flex items-center justify-center gap-2 brand-glow disabled:opacity-50"
              >
                <Download className="h-4 w-4" /> Download 15-Day Archive (.zip)
              </button>
              
              <button
                onClick={clearOld}
                disabled={busy || !status || status.old_bookings === 0}
                className="w-full h-12 bg-destructive text-destructive-foreground rounded-full font-display font-bold flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Trash2 className="h-4 w-4" /> Clear Database (Older than 15 days)
              </button>
            </div>
          </div>
        )}

        <div className="mt-6 border-t border-border pt-4 flex justify-end">
          <button onClick={onClose} className="h-10 px-6 bg-muted rounded-full font-display font-bold text-sm">Close</button>
        </div>
      </motion.div>
    </motion.div>
  );
}
