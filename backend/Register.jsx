import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Phone, ArrowRight, Camera, Upload, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { api, fileToBase64 } from "@/lib/api";
import Stepper from "@/components/Stepper";

export default function Register() {
  const nav = useNavigate();
  const [phone, setPhone] = useState("");
  const [photo, setPhoto] = useState("");

  useEffect(() => {
    // Background wake up backend
    api.get("/categories").catch(() => {});
  }, []);

  const handlePhoto = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 50 * 1024 * 1024) { toast.error("Photo must be under 50MB"); return; }
    const b64 = await fileToBase64(file);
    setPhoto(b64);
    sessionStorage.setItem("anjana_photo", b64);
  };

  const submit = (e) => {
    e.preventDefault();
    if (!phone) {
      toast.error("Please enter your Phone Number"); return;
    }
    if (!/^\d{10}$/.test(phone.replace(/\D/g, "").slice(-10))) {
      toast.error("Enter a valid 10-digit phone number"); return;
    }
    if (!photo) {
      toast.error("Please click your vehicle photo"); return;
    }
    
    // Save combined details
    sessionStorage.setItem("anjana_details", JSON.stringify({
      customer_name: "Customer",
      phone: phone.trim(),
      vehicle_number: "" // vehicle number is removed
    }));
    sessionStorage.setItem("anjana_photo", photo);
    
    nav("/category");
  };

  return (
    <div className="mx-auto max-w-lg px-6 py-10" data-testid="register-page">
      <Stepper step={1} />
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight mt-4">Your details</h1>
        <p className="text-muted-foreground mt-2">Enter your phone number and take a quick photo of your vehicle.</p>
      </motion.div>

      <form onSubmit={submit} className="mt-8 space-y-6">
        <Field icon={Phone} label="Phone Number">
          <input
            data-testid="input-phone"
            type="text"
            inputMode="numeric"
            value={phone}
            onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 10))}
            className="input-field font-mono text-lg"
            placeholder="Enter your phone number"
            autoComplete="off"
            required
          />
        </Field>

        <div>
          <div className="label-caps mb-2 flex items-center gap-2">
            <Camera className="h-3.5 w-3.5" strokeWidth={2.5} />
            Vehicle Photo
          </div>
          <label className="block cursor-pointer group" data-testid="vehicle-photo-upload">
            <input type="file" accept="image/*" capture="environment" onChange={handlePhoto} className="sr-only" />
            {photo ? (
              <div className="relative border border-border rounded-[14px] overflow-hidden elev-2">
                <img src={photo} alt="vehicle" className="w-full h-64 object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <div className="absolute top-3 right-3 chip bg-background/90 backdrop-blur">
                  <CheckCircle2 className="h-3 w-3" strokeWidth={3} style={{ color: "hsl(var(--success))" }} /> Ready
                </div>
                <div className="absolute bottom-3 right-3 chip bg-background/90 backdrop-blur">
                  <Upload className="h-3 w-3" strokeWidth={2.5} /> Tap to replace
                </div>
              </div>
            ) : (
              <div className="border border-dashed border-border rounded-[14px] h-64 grid place-items-center bg-muted/50 group-hover:bg-muted group-hover:border-primary/40 transition-colors">
                <div className="text-center p-6">
                  <div className="h-14 w-14 rounded-full bg-card border border-border grid place-items-center mx-auto elev-1">
                    <Camera className="h-6 w-6 text-primary" strokeWidth={2.5} />
                  </div>
                  <div className="mt-3 font-display font-black text-base sm:text-lg flex flex-col items-center">
                    <span>Click your vehicle photo</span>
                    <span className="text-sm mt-0.5 text-muted-foreground">ನಿಮ್ಮ ವಾಹನದ ಫೋಟೋ ಕ್ಲಿಕ್ ಮಾಡಿ</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">JPG/PNG · under 50MB</div>
                </div>
              </div>
            )}
          </label>
        </div>

        <button
          type="submit"
          data-testid="submit-registration"
          className="group w-full h-14 bg-primary text-primary-foreground font-display font-bold text-lg rounded-full brand-glow elev-lift flex items-center justify-center gap-2"
        >
          Continue to Vehicle
          <span className="h-7 w-7 grid place-items-center rounded-full bg-primary-foreground/15 group-hover:translate-x-0.5 transition-transform">
            <ArrowRight className="h-4 w-4" strokeWidth={2.5} />
          </span>
        </button>
      </form>
    </div>
  );
}

function Field({ icon: Icon, label, children }) {
  return (
    <div>
      <div className="label-caps mb-2 flex items-center gap-2">
        <Icon className="h-3.5 w-3.5" strokeWidth={2.5} />
        {label}
      </div>
      {children}
    </div>
  );
}
