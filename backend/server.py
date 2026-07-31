from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware

import os
import logging
import io
import zipfile
import csv
import base64
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    try:
        from backend.postgres_db import PostgresDB
    except ModuleNotFoundError:
        from postgres_db import PostgresDB
    db = PostgresDB(DATABASE_URL)
else:
    try:
        from backend.sqlite_db import SQLiteDB
    except ModuleNotFoundError:
        from sqlite_db import SQLiteDB
    db = SQLiteDB(str(ROOT_DIR / 'anjana_clean.db'))
client = db

app = FastAPI(title="Anjana Wash API")
api_router = APIRouter(prefix="/api")

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )

IST_OFFSET = timedelta(hours=5, minutes=30)


def now_ist_iso() -> str:
    return (datetime.now(timezone.utc) + IST_OFFSET).replace(tzinfo=None).isoformat()


def today_key() -> str:
    # YYYY-MM-DD in IST
    return (datetime.now(timezone.utc) + IST_OFFSET).strftime("%Y-%m-%d")


# ---------- Models ----------
class Service(BaseModel):
    id: str
    category_id: str
    name: str
    price: int
    description: str = ""
    active: bool = True


class ServiceCreate(BaseModel):
    owner_pin: str
    category_id: str
    name: str
    price: int
    description: str = ""


class ServiceUpdate(BaseModel):
    owner_pin: str
    name: Optional[str] = None
    price: Optional[int] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class ServiceDelete(BaseModel):
    owner_pin: str


# Categories: static tree (stable ids). Car has sub-categories; others are leaves.
CATEGORIES = [
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
]


def flatten_leaf_categories():
    leaves = []
    for c in CATEGORIES:
        if c["children"]:
            for ch in c["children"]:
                leaves.append({"id": ch["id"], "label": ch["label"], "parent_id": c["id"], "parent_label": c["label"]})
        else:
            leaves.append({"id": c["id"], "label": c["label"], "parent_id": None, "parent_label": None})
    return leaves


LEAF_BY_ID = {lf["id"]: lf for lf in flatten_leaf_categories()}


DEFAULT_SERVICE_PRICES = {
    "small_car": [
        ("Only Water", 100, "Water wash only"),
        ("Water + Dry", 150, "Water wash and drying"),
        ("Outside Wash", 250, "Exterior wash"),
        ("Body Wash", 350, "Full body wash"),
        ("Full Wash", 450, "Premium full wash"),
        ("Inside Vacuum", 100, "Interior vacuum cleaning"),
        ("Under Chassis Wash", 150, "Undercarriage cleaning"),
        ("Engine Wash", 100, "Engine bay cleaning")
    ],
    "xuv": [
        ("Only Water", 150, "Water wash only"),
        ("Water + Dry", 200, "Water wash and drying"),
        ("Outside Wash", 300, "Exterior wash"),
        ("Body Wash", 450, "Full body wash"),
        ("Full Wash", 550, "Premium full wash"),
        ("Inside Vacuum", 150, "Interior vacuum cleaning"),
        ("Under Chassis Wash", 200, "Undercarriage cleaning"),
        ("Engine Wash", 150, "Engine bay cleaning")
    ],
    "7seater": [
        ("Only Water", 180, "Water wash only"),
        ("Water + Dry", 250, "Water wash and drying"),
        ("Outside Wash", 350, "Exterior wash"),
        ("Body Wash", 550, "Full body wash"),
        ("Full Wash", 700, "Premium full wash"),
        ("Inside Vacuum", 200, "Interior vacuum cleaning"),
        ("Under Chassis Wash", 250, "Undercarriage cleaning"),
        ("Engine Wash", 200, "Engine bay cleaning")
    ],
    "auto": [
        ("Water Full body", 200, "Complete body water wash"),
        ("Water only body", 150, "Body water wash only"),
        ("Water Engine", 150, "Engine water wash"),
        ("Body wash", 400, "Standard body wash"),
        ("Full wash", 500, "Premium full wash"),
        ("Full wash + Diesel spray", 550, "Full wash with diesel spray finish")
    ],
    "ape_auto": [
        ("Water Full body", 300, "Complete body water wash"),
        ("Body wash", 500, "Standard body wash"),
        ("Full wash", 600, "Premium full wash"),
        ("Full wash + Diesel spray", 650, "Full wash with diesel spray finish")
    ],
    "tt": [
        ("Only Body Water", 350, "Body water wash only"),
        ("Body wash", 600, "Standard body wash"),
        ("Full wash", 750, "Premium full wash"),
        ("Full wash + Diesel spray", 800, "Full wash with diesel spray finish"),
        ("Full wash + Grease", 800, "Full wash with grease service"),
        ("Under Chassis Wash", 400, "Undercarriage cleaning"),
        ("Under Chassis Wash + Grease", 500, "Undercarriage cleaning and grease service"),
        ("Only Inside Air + Mat clean", 400, "Interior air cleaning and mat wash")
    ],
    "tata_ace": [
        ("Body wash", 500, "Standard body wash"),
        ("Full wash", 700, "Premium full wash"),
        ("Full wash + Grease", 750, "Full wash with grease service"),
        ("Under Chassis Wash", 350, "Undercarriage cleaning"),
        ("Under Chassis + Grease", 450, "Undercarriage cleaning and grease service")
    ],
    "bolero_leyland": [
        ("Body wash", 600, "Standard body wash"),
        ("Full wash", 800, "Premium full wash"),
        ("Full wash + Grease", 850, "Full wash with grease service"),
        ("Full wash + Grease + Diesel spray", 900, "Full wash with grease and diesel spray finish")
    ],
    "bike": [
        ("Water", 80, "Water wash only"),
        ("Foam Wash", 150, "Foam wash"),
        ("Foam Wash + Diesel Spray", 180, "Foam wash and diesel spray"),
        ("Chain Diesel Wash", 80, "Chain diesel wash")
    ],
    "scooter": [
        ("Water", 80, "Water wash only"),
        ("Foam Wash", 120, "Foam wash"),
        ("Foam Wash + Diesel Spray", 150, "Foam wash and diesel spray")
    ],
    "tractor": [
        ("Only Engine Water", 400, "Engine water wash only"),
        ("Only Engine Foam Wash", 700, "Engine foam wash only"),
        ("Only Engine Foam + Diesel Spray", 750, "Engine foam wash and diesel spray only"),
        ("Engine + Trolley Water", 700, "Engine and trolley water wash"),
        ("Engine + Trolley Full Wash + Diesel Spray", 1200, "Engine and trolley full wash with diesel spray"),
        ("Trolley Wash Foam + Diesel Spray", 700, "Trolley foam wash with diesel spray"),
        ("Engine Greasing", 250, "Engine greasing service")
    ],
    "jcb": [
        ("Only Water", 1300, "Water wash only"),
        ("Full Wash with Foam and Diesel Spray", 2800, "Full wash with foam and diesel spray"),
        ("Greasing", 400, "Greasing service")
    ],
    "others": [
        ("Others 200", 200, "Other custom service - ₹200"),
        ("Others 500", 500, "Other custom service - ₹500"),
        ("Others 1000", 1000, "Other custom service - ₹1000"),
        ("Others 1500", 1500, "Other custom service - ₹1500"),
        ("Others 2000", 2000, "Other custom service - ₹2000"),
        ("Others 2500", 2500, "Other custom service - ₹2500"),
        ("Others 3000", 3000, "Other custom service - ₹3000")
    ]
}


class BookingCreate(BaseModel):
    customer_name: str
    phone: str
    vehicle_number: str
    vehicle_photo: str  # base64 data URL
    category_id: str  # leaf category id (e.g., "small_car", "bike")
    service_id: str  # uuid of a service in db.services
    payment_method: str  # "cash" or "online"
    payment_provider: Optional[str] = None  # "phonepe" | "gpay" when online
    worker_photo: Optional[str] = None
    booking_source: Optional[str] = "walkin"


class Booking(BaseModel):
    id: str
    token: str
    customer_name: str
    phone: str
    vehicle_number: str
    vehicle_photo: Optional[str] = ""
    category_id: str
    category_label: str
    parent_category_id: Optional[str] = None
    parent_category_label: Optional[str] = None
    service_id: str
    service_name: str
    price: int
    payment_method: str
    payment_provider: Optional[str] = None
    payment_status: str  # pending / paid
    status: str  # queued / completed
    worker_photo: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    booking_source: Optional[str] = "walkin"


class CompleteBookingRequest(BaseModel):
    worker_photo: Optional[str] = None  # required if cash


class PinRequest(BaseModel):
    role: str  # "worker" or "owner"
    pin: str


class UpdatePinRequest(BaseModel):
    owner_pin: str  # for auth
    role: str  # "worker" or "owner"
    new_pin: str


class OwnerActionRequest(BaseModel):
    owner_pin: str


class PaymentInitiateRequest(BaseModel):
    booking_id: str


# ---------- Helpers ----------
SERVICES_CACHE = {}

async def get_service_doc(service_id: str):
    if service_id in SERVICES_CACHE:
        return SERVICES_CACHE[service_id]
    doc = await db.services.find_one({"id": service_id, "active": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or inactive service")
    SERVICES_CACHE[service_id] = doc
    return doc


PIN_CACHE = {
    "worker_pin": "1234",
    "owner_pin": "9999"
}

LAST_STATUS_CHECK = {}


async def verify_owner_pin_or_raise(pin: str):
    if PIN_CACHE.get("owner_pin") != pin:
        raise HTTPException(403, "Invalid owner PIN")


async def verify_worker_or_owner_pin_or_raise(pin: str):
    if PIN_CACHE.get("owner_pin") != pin and PIN_CACHE.get("worker_pin") != pin:
        raise HTTPException(403, "Invalid PIN")


async def generate_daily_token() -> str:
    today = today_key()
    counter = await db.counters.find_one_and_update(
        {"_id": f"token-{today}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = counter["seq"] if counter else 1
    return f"T-{seq:03d}"


async def init_config():
    global PIN_CACHE
    existing = await db.config.find_one({"_id": "pins"}, {"_id": 0})
    if not existing:
        await db.config.insert_one({"_id": "pins", "worker_pin": "1234", "owner_pin": "9999"})
        PIN_CACHE = {"worker_pin": "1234", "owner_pin": "9999"}
    else:
        PIN_CACHE = {
            "worker_pin": existing.get("worker_pin", "1234"),
            "owner_pin": existing.get("owner_pin", "9999")
        }


async def init_services():
    count = await db.services.count_documents({})
    if count > 0:
        return
    seeds = []
    for cat_id, items in DEFAULT_SERVICE_PRICES.items():
        for name, price, desc in items:
            seeds.append({
                "id": str(uuid.uuid4()),
                "category_id": cat_id,
                "name": name,
                "price": price,
                "description": desc,
                "active": True,
            })
    if seeds:
        await db.services.insert_many(seeds)


async def migrate_legacy_bookings():
    # Backfill bookings inserted before category fields existed so response_model validation doesn't 500.
    await db.bookings.update_many(
        {"category_id": {"$exists": False}},
        {"$set": {
            "category_id": "small_car",
            "category_label": "Small Car",
            "parent_category_id": "car",
            "parent_category_label": "Car",
        }},
    )


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "Anjana Wash API"}


@api_router.get("/categories")
async def list_categories():
    return CATEGORIES


@api_router.get("/services", response_model=List[Service])
async def list_services():
    cursor = db.services.find({"active": True}, {"_id": 0}).sort("price", 1)
    return await cursor.to_list(500)


@api_router.get("/services/by-category/{category_id}", response_model=List[Service])
async def services_by_category(category_id: str):
    if category_id not in LEAF_BY_ID:
        raise HTTPException(400, "Invalid category")
    cursor = db.services.find({"category_id": category_id, "active": True}, {"_id": 0}).sort("price", 1)
    results = await cursor.to_list(100)
    
    if not results and category_id in DEFAULT_SERVICE_PRICES:
        import random
        for name, price, desc in DEFAULT_SERVICE_PRICES[category_id]:
            svc_id = f"{category_id}_{name.lower().replace(' ', '_')}_{random.randint(100, 999)}"
            await db.services.insert_one({
                "id": svc_id,
                "category_id": category_id,
                "name": name,
                "price": price,
                "description": desc,
                "active": True
            })
        cursor = db.services.find({"category_id": category_id, "active": True}, {"_id": 0}).sort("price", 1)
        results = await cursor.to_list(100)
        
    return results


@api_router.get("/owner/services", response_model=List[Service])
async def owner_list_services(owner_pin: str):
    await verify_owner_pin_or_raise(owner_pin)
    # returns all services incl. inactive (owner can toggle)
    cursor = db.services.find({}, {"_id": 0}).sort([("category_id", 1), ("price", 1)])
    return await cursor.to_list(500)


@api_router.post("/owner/services", response_model=Service)
async def owner_create_service(payload: ServiceCreate):
    await verify_owner_pin_or_raise(payload.owner_pin)
    if payload.category_id not in LEAF_BY_ID:
        raise HTTPException(400, "Invalid category")
    if payload.price <= 0 or not payload.name.strip():
        raise HTTPException(400, "Invalid service data")
    svc = Service(
        id=str(uuid.uuid4()),
        category_id=payload.category_id,
        name=payload.name.strip(),
        price=payload.price,
        description=payload.description.strip(),
        active=True,
    )
    await db.services.insert_one(svc.model_dump())
    SERVICES_CACHE.clear()
    return svc


@api_router.patch("/owner/services/{service_id}", response_model=Service)
async def owner_update_service(service_id: str, payload: ServiceUpdate):
    await verify_owner_pin_or_raise(payload.owner_pin)
    existing = await db.services.find_one({"id": service_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Service not found")
    update = {}
    if payload.name is not None and payload.name.strip():
        update["name"] = payload.name.strip()
    if payload.price is not None and payload.price > 0:
        update["price"] = payload.price
    if payload.description is not None:
        update["description"] = payload.description.strip()
    if payload.active is not None:
        update["active"] = payload.active
    if update:
        await db.services.update_one({"id": service_id}, {"$set": update})
        SERVICES_CACHE.clear()
    doc = await db.services.find_one({"id": service_id}, {"_id": 0})
    return doc


@api_router.delete("/owner/services/{service_id}")
async def owner_delete_service(service_id: str, payload: ServiceDelete):
    await verify_owner_pin_or_raise(payload.owner_pin)
    res = await db.services.delete_one({"id": service_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Service not found")
    SERVICES_CACHE.clear()
    return {"success": True}


import time
from collections import defaultdict

# IP-based rate limiter (max 20 bookings per minute per IP)
booking_rate_limit = defaultdict(list)

def check_booking_rate_limit(ip: str) -> bool:
    now = time.time()
    booking_rate_limit[ip] = [t for t in booking_rate_limit[ip] if now - t < 60]
    if len(booking_rate_limit[ip]) >= 20:
        return False
    booking_rate_limit[ip].append(now)
    return True

@api_router.post("/bookings", response_model=Booking)
async def create_booking(payload: BookingCreate, request: Request):
    client_ip = request.client.host if request and request.client else "unknown"
    if not check_booking_rate_limit(client_ip):
        raise HTTPException(429, "Too many bookings created. Please wait a minute.")
    if payload.payment_method not in ("cash", "online"):
        raise HTTPException(400, "Invalid payment method")
    if payload.payment_method == "online" and payload.payment_provider not in ("phonepe", "gpay"):
        raise HTTPException(400, "Invalid payment provider for online method")
    if payload.category_id not in LEAF_BY_ID:
        raise HTTPException(400, "Invalid category")
    
    service_ids = [sid.strip() for sid in payload.service_id.split(",") if sid.strip()]
    if not service_ids:
        raise HTTPException(400, "No services selected")
        
    services = []
    for sid in service_ids:
        svc = await get_service_doc(sid)
        if svc["category_id"] != payload.category_id:
            raise HTTPException(400, f"Service {svc['name']} does not belong to the selected category")
        services.append(svc)
        
    total_price = sum(s["price"] for s in services)
    combined_names = ", ".join(s["name"] for s in services)
    
    leaf = LEAF_BY_ID[payload.category_id]
    if payload.payment_method == "online":
        token = "Pending Payment"
        status = "pending"
    else:
        token = await generate_daily_token()
        status = "queued"
    
    booking = Booking(
        id=str(uuid.uuid4()),
        token=token,
        customer_name=payload.customer_name.strip(),
        phone=payload.phone.strip(),
        vehicle_number=payload.vehicle_number.strip().upper(),
        vehicle_photo=payload.vehicle_photo,
        category_id=payload.category_id,
        category_label=leaf["label"],
        parent_category_id=leaf["parent_id"],
        parent_category_label=leaf["parent_label"],
        service_id=payload.service_id,
        service_name=combined_names,
        price=total_price,
        payment_method=payload.payment_method,
        payment_provider=payload.payment_provider if payload.payment_method == "online" else None,
        payment_status="pending",
        status=status,
        worker_photo=payload.worker_photo,
        created_at=now_ist_iso(),
        booking_source=payload.booking_source or "walkin"
    )
    doc = booking.model_dump()
    await db.bookings.insert_one(doc)
    return booking


@api_router.get("/bookings/latest-id")
async def get_latest_id():
    cursor = db.bookings.find(
        {"status": "queued", "$or": [{"payment_method": "cash"}, {"payment_status": "paid"}]},
        {"id": 1}
    ).sort("created_at", -1)
    res = await cursor.to_list(1)
    return {"latest_id": res[0]["id"] if res else ""}


async def auto_cleanup_old_photos():
    try:
        from datetime import datetime, timedelta
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        fifteen_days_ago = (now_ist - timedelta(days=15)).isoformat()
        seven_days_ago = (now_ist - timedelta(days=7)).isoformat()
        
        # 1. Clear heavy Base64 image strings older than 15 days to keep DB size < 5MB
        await db.bookings.update_many(
            {"created_at": {"$lt": fifteen_days_ago}},
            {"$set": {"vehicle_photo": "", "worker_photo": ""}}
        )
        
        # 2. Purge abandoned/unpaid draft attempts older than 7 days
        await db.bookings.delete_many(
            {
                "created_at": {"$lt": seven_days_ago},
                "payment_status": "pending",
                "payment_method": "online"
            }
        )
        
        # 3. Flush in-memory status check cache to prevent memory buildup
        if len(LAST_STATUS_CHECK) > 100:
            LAST_STATUS_CHECK.clear()
            
        logger.info("Automatic database photo purging and cache cleanup finished.")
    except Exception as ex:
        logger.error(f"Automatic database cleanup failed: {str(ex)}")


LAST_CLEANUP = 0
def extract_phonepe_state(res_data: dict) -> str:
    if not isinstance(res_data, dict):
        return ""
    
    # 1. Direct top-level fields
    state = res_data.get("state") or res_data.get("status") or res_data.get("paymentState")
    if state and isinstance(state, str):
        return state.upper()
        
    # 2. Check inside "data" sub-object
    data_obj = res_data.get("data")
    if isinstance(data_obj, dict):
        d_state = data_obj.get("state") or data_obj.get("status") or data_obj.get("paymentState")
        if d_state and isinstance(d_state, str):
            return d_state.upper()
            
    # 3. Check "code" field
    code = res_data.get("code")
    if code in ("PAYMENT_SUCCESS", "SUCCESS", "COMPLETED"):
        return "COMPLETED"
    elif code in ("PAYMENT_ERROR", "PAYMENT_DECLINED", "CANCELLED", "EXPIRED"):
        return "FAILED"
        
    return ""

LAST_SYNC_TIME = 0

def is_phonepe_production() -> bool:
    env = os.environ.get("PHONEPE_ENV", "sandbox").strip().lower()
    client_id = os.environ.get("PHONEPE_CLIENT_ID", "").strip()
    # If set to sandbox, or if client_id is a Sandbox ID (starts with SU), use test/sandbox mode
    if env == "sandbox" or client_id.startswith("SU") or not client_id:
        return False
    return env == "production"

async def sync_pending_bookings():
    global LAST_SYNC_TIME
    import time
    now_ts = time.time()
    # Throttle: Only query PhonePe API status at most once every 15 seconds to make dashboard loading instant
    if now_ts - LAST_SYNC_TIME < 15:
        return
    LAST_SYNC_TIME = now_ts

    from datetime import datetime, timedelta
    now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    # Check pending bookings created in the last 24 hours
    twenty_four_hours_ago = (now_ist - timedelta(hours=24)).isoformat()
    
    try:
        cursor_pending = db.bookings.find(
            {
                "payment_method": "online",
                "payment_status": "pending"
            }
        )
        all_pending = await cursor_pending.to_list(100)
        pending_list = [b for b in all_pending if b.get("created_at", "") >= twenty_four_hours_ago]
        
        for b in pending_list:
            booking_id = b["id"]
            client_id = os.environ.get("PHONEPE_CLIENT_ID")
            client_secret = os.environ.get("PHONEPE_CLIENT_SECRET")
            if not is_phonepe_production():
                await _payment_callback(booking_id)
            elif client_id and client_secret:
                try:
                    token = await _get_oauth_token()
                    sanitized_id = booking_id.replace("-", "")
                    url = f"https://api.phonepe.com/apis/pg/checkout/v2/order/{sanitized_id}/status"
                    headers = {"Authorization": f"O-Bearer {token}"}
                    import asyncio
                    res = await asyncio.to_thread(requests.get, url, headers=headers, timeout=3)
                    if res.status_code == 200:
                        res_data = res.json()
                        state = extract_phonepe_state(res_data)
                        if state == "COMPLETED":
                            await _payment_callback(booking_id)
                        elif state in ("FAILED", "EXPIRED", "CANCELLED"):
                            await db.bookings.delete_one({"id": booking_id})
                except Exception as ex:
                    logger.error(f"Background PhonePe sync failed for {booking_id}: {str(ex)}")
    except Exception as e:
        logger.error(f"Failed to query pending bookings for auto-sync: {str(e)}")


@api_router.get("/bookings/queue", response_model=List[Booking])
async def queue():
    global LAST_CLEANUP
    import time, asyncio
    now_ts = time.time()
    if now_ts - LAST_CLEANUP > 43200:  # every 12 hours
        LAST_CLEANUP = now_ts
        asyncio.create_task(auto_cleanup_old_photos())

    # Automatically verify/sync any pending online bookings created in the last 24 hours
    await sync_pending_bookings()

    # Return active queued bookings (paid online or any cash bookings)
    cursor = db.bookings.find(
        {"status": "queued", "$or": [{"payment_method": "cash"}, {"payment_status": "paid"}]},
        {"_id": 0, "vehicle_photo": 0},
    ).sort("created_at", 1)
    items = await cursor.to_list(500)
    res = []
    for b in items:
        res.append(await ensure_booking_token(b))
    return res


@api_router.get("/bookings", response_model=List[Booking])
async def all_bookings(date: Optional[str] = None, pin: Optional[str] = None):
    today = today_key()
    if not date or date != today:
        if not pin:
            raise HTTPException(401, "PIN required for historical bookings")
        await verify_worker_or_owner_pin_or_raise(pin)
    
    # Sync pending bookings before retrieving list
    await sync_pending_bookings()
    
    q = {}
    if date:
        q["created_at"] = {"$regex": f"^{date}"}
    cursor = db.bookings.find(q, {"_id": 0, "vehicle_photo": 0}).sort("created_at", -1)
    items = await cursor.to_list(1000)
    res = []
    for b in items:
        res.append(await ensure_booking_token(b))
    return res


@api_router.get("/bookings/{booking_id}", response_model=Booking)
async def get_booking(booking_id: str):
    doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Booking not found")
        
    # Auto-check status if online phonepe and pending
    if doc.get("payment_method") == "online" and doc.get("payment_provider") == "phonepe" and doc.get("payment_status") == "pending":
        import time
        now = time.time()
        last_check = LAST_STATUS_CHECK.get(booking_id, 0)
        if now - last_check > 10:
            LAST_STATUS_CHECK[booking_id] = now
            client_id = os.environ.get("PHONEPE_CLIENT_ID")
            client_secret = os.environ.get("PHONEPE_CLIENT_SECRET")
            if client_id and client_secret:
                try:
                    token = await _get_oauth_token()
                    env = os.environ.get("PHONEPE_ENV", "sandbox")
                    
                    sanitized_id = booking_id.replace("-", "")
                    if env == "production":
                        url = f"https://api.phonepe.com/apis/pg/checkout/v2/order/{sanitized_id}/status"
                    else:
                        url = f"https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/order/{sanitized_id}/status"
                        
                    headers = {
                        "Authorization": f"O-Bearer {token}"
                    }
                    
                    import asyncio
                    res = await asyncio.to_thread(requests.get, url, headers=headers, timeout=5)
                    res_data = res.json()
                    
                    # Check status using extract_phonepe_state
                    state = extract_phonepe_state(res_data)
                    if state == "COMPLETED":
                        await _payment_callback(booking_id)
                        doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
                    elif state in ("FAILED", "EXPIRED", "CANCELLED"):
                        await db.bookings.delete_one({"id": booking_id})
                        raise HTTPException(400, "Payment failed or cancelled")
                except Exception as e:
                    logger.error(f"Error auto-checking PhonePe status for booking {booking_id}: {str(e)}")
                
    return await ensure_booking_token(doc)


@api_router.get("/bookings/{booking_id}/photo")
async def get_booking_photo(booking_id: str):
    doc = await db.bookings.find_one({"id": booking_id})
    if not doc or not doc.get("vehicle_photo"):
        raise HTTPException(404, "Photo not found")
        
    b64_data = doc["vehicle_photo"]
    if "," in b64_data:
        b64_data = b64_data.split(",")[1]
        
    try:
        img_bytes = base64.b64decode(b64_data)
        from fastapi.responses import Response
        return Response(
            content=img_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=604800"}
        )
    except Exception:
        raise HTTPException(400, "Invalid image data")


@api_router.post("/bookings/{booking_id}/complete", response_model=Booking)
async def complete_booking(booking_id: str, payload: CompleteBookingRequest = CompleteBookingRequest()):
    doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Booking not found")
    if doc["status"] == "completed":
        raise HTTPException(400, "Already completed")

    update = {
        "status": "completed",
        "completed_at": now_ist_iso(),
    }
    if doc["payment_method"] == "cash":
        update["worker_photo"] = payload.worker_photo or doc.get("worker_photo")
        update["payment_status"] = "paid"
    if payload.worker_photo and doc["payment_method"] != "cash":
        update["worker_photo"] = payload.worker_photo

    await db.bookings.update_one({"id": booking_id}, {"$set": update})
    new_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    return new_doc


@api_router.post("/bookings/{booking_id}/mark-paid", response_model=Booking)
async def owner_mark_paid(booking_id: str, payload: OwnerActionRequest):
    await verify_owner_pin_or_raise(payload.owner_pin)
    doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Booking not found")
    await db.bookings.update_one({"id": booking_id}, {"$set": {"payment_status": "paid"}})
    new_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    return new_doc


@api_router.get("/bookings/stats/today")
async def today_stats(pin: Optional[str] = None):
    if pin:
        await verify_worker_or_owner_pin_or_raise(pin)
    today = today_key()
    cursor = db.bookings.find({"created_at": {"$regex": f"^{today}"}}, {"_id": 0})
    items = await cursor.to_list(1000)
    paid = [b for b in items if b["payment_status"] == "paid"]
    cash = [b for b in paid if b["payment_method"] == "cash"]
    online = [b for b in paid if b["payment_method"] == "online"]
    completed = [b for b in items if b["status"] == "completed"]

    return {
        "date": today,
        "total_bookings": len(items),
        "completed": len(completed),
        "pending": len([b for b in items if b["status"] == "queued"]),
        "cash_count": len(cash),
        "online_count": len(online),
        "cash_amount": sum(b["price"] for b in cash),
        "online_amount": sum(b["price"] for b in online),
        "total_earnings": sum(b["price"] for b in paid),
    }


class ClearRequest(BaseModel):
    owner_pin: str


@api_router.get("/bookings/archive/status")
async def archive_status():
    cursor = db.bookings.find()
    all_b = await cursor.to_list(50000)
    
    cutoff_dt = datetime.now(timezone.utc) + IST_OFFSET - timedelta(days=15)
    cutoff_str = cutoff_dt.isoformat()
    
    old_b = [b for b in all_b if b["created_at"] < cutoff_str]
    return {
        "total_bookings": len(all_b),
        "old_bookings": len(old_b),
        "cutoff_date": cutoff_str
    }


@api_router.post("/owner/clear-today-tokens")
async def clear_today_tokens_endpoint(req: OwnerActionRequest):
    await verify_owner_pin_or_raise(req.pin)
    today = today_key()
    cursor = db.bookings.find({})
    all_b = await cursor.to_list(10000)
    today_b = [b for b in all_b if b.get("created_at", "").startswith(today)]
    
    count = 0
    for b in today_b:
        await db.bookings.delete_one({"id": b["id"]})
        count += 1
        
    await db.counters.find_one_and_update(
        {"_id": f"token-{today}"},
        {"$set": {"seq": 0}},
        upsert=True
    )
    return {"success": True, "deleted_count": count, "message": f"Cleared {count} bookings and reset token counter for today."}

@api_router.get("/bookings/archive/download")
async def download_archive(owner_pin: str, all: bool = False):
    await verify_owner_pin_or_raise(owner_pin)
    
    cursor = db.bookings.find()
    all_b = await cursor.to_list(50000)
    
    if not all:
        cutoff_dt = datetime.now(timezone.utc) + IST_OFFSET - timedelta(days=15)
        cutoff_str = cutoff_dt.isoformat()
        bookings_to_archive = [b for b in all_b if b["created_at"] < cutoff_str]
    else:
        bookings_to_archive = all_b
        
    if not bookings_to_archive:
        raise HTTPException(status_code=400, detail="No bookings found to archive")
        
    from fastapi.responses import StreamingResponse
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as archive:
        csv_io = io.StringIO()
        writer = csv.writer(csv_io)
        writer.writerow([
            "ID", "Token", "Customer Name", "Phone", "Vehicle Number", 
            "Category", "Service Name", "Price", "Payment Method", 
            "Payment Provider", "Payment Status", "Status", "Created At", "Completed At"
        ])
        
        for b in bookings_to_archive:
            writer.writerow([
                b.get("id"),
                b.get("token"),
                b.get("customer_name"),
                b.get("phone"),
                b.get("vehicle_number"),
                b.get("category_label"),
                b.get("service_name"),
                b.get("price"),
                b.get("payment_method"),
                b.get("payment_provider"),
                b.get("payment_status"),
                b.get("status"),
                b.get("created_at"),
                b.get("completed_at")
            ])
            
            for photo_type in ["vehicle_photo", "worker_photo"]:
                photo_data = b.get(photo_type)
                if photo_data and "base64," in photo_data:
                    try:
                        header, base64_str = photo_data.split("base64,", 1)
                        ext = "jpg"
                        if "image/png" in header:
                            ext = "png"
                        elif "image/webp" in header:
                            ext = "webp"
                        image_bytes = base64.b64decode(base64_str)
                        filename = f"photos/{b.get('token')}_{b.get('id')[:8]}_{photo_type}.{ext}"
                        archive.writestr(filename, image_bytes)
                    except Exception as e:
                        logger.error(f"Error writing image to zip: {str(e)}")
                        
        archive.writestr("bookings.csv", csv_io.getvalue())
        
    zip_io.seek(0)
    date_str = (datetime.now(timezone.utc) + IST_OFFSET).strftime("%Y%m%d_%H%M%S")
    filename = f"anjana_wash_archive_{date_str}.zip"
    
    return StreamingResponse(
        zip_io,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.post("/bookings/archive/clear")
async def clear_archive(payload: ClearRequest):
    await verify_owner_pin_or_raise(payload.owner_pin)
    
    cursor = db.bookings.find()
    all_b = await cursor.to_list(50000)
    
    cutoff_dt = datetime.now(timezone.utc) + IST_OFFSET - timedelta(days=15)
    cutoff_str = cutoff_dt.isoformat()
    
    old_bookings = [b for b in all_b if b["created_at"] < cutoff_str]
    
    deleted_count = 0
    for b in old_bookings:
        res = await db.bookings.delete_one({"id": b["id"]})
        deleted_count += res.deleted_count
        
    return {"success": True, "deleted_count": deleted_count}


# ---------- PIN ----------
@api_router.post("/auth/verify-pin")
async def verify_pin(payload: PinRequest):
    key = f"{payload.role}_pin"
    if key not in PIN_CACHE:
        raise HTTPException(400, "Invalid role")
    return {"success": PIN_CACHE[key] == payload.pin}


@api_router.post("/auth/update-pin")
async def update_pin(payload: UpdatePinRequest):
    if PIN_CACHE.get("owner_pin") != payload.owner_pin:
        raise HTTPException(403, "Invalid owner PIN")
    if payload.role not in ("worker", "owner"):
        raise HTTPException(400, "Invalid role")
    if not (payload.new_pin.isdigit() and 4 <= len(payload.new_pin) <= 6):
        raise HTTPException(400, "PIN must be 4-6 digits")
    await db.config.update_one(
        {"_id": "pins"},
        {"$set": {f"{payload.role}_pin": payload.new_pin}},
    )
    # Update memory cache
    PIN_CACHE[f"{payload.role}_pin"] = payload.new_pin
    return {"success": True}


# ---------- PhonePe & GPay Payment Gateways ----------
import base64
import json
import requests
from fastapi import Request

OAUTH_TOKEN_CACHE = {
    "token": None,
    "expires_at": 0
}

async def _get_oauth_token():
    import time
    now = time.time()
    if OAUTH_TOKEN_CACHE["token"] and OAUTH_TOKEN_CACHE["expires_at"] > now:
        return OAUTH_TOKEN_CACHE["token"]

    client_id = os.environ.get("PHONEPE_CLIENT_ID")
    client_secret = os.environ.get("PHONEPE_CLIENT_SECRET")
    client_version = os.environ.get("PHONEPE_CLIENT_VERSION", "1")
    env = os.environ.get("PHONEPE_ENV", "sandbox")
    
    if env == "production":
        url = "https://api.phonepe.com/apis/identity-manager/v1/oauth/token"
    else:
        url = "https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token"
        
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_version": client_version,
        "grant_type": "client_credentials"
    }
    
    import urllib.parse
    encoded_data = urllib.parse.urlencode(data)
    
    try:
        import asyncio
        response = await asyncio.to_thread(requests.post, url, data=encoded_data, headers=headers, timeout=10)
        res_json = response.json()
    except Exception as e:
        logger.error(f"PhonePe OAuth network/json error: {str(e)}")
        raise HTTPException(502, f"PhonePe authorization request failed: Network Error")
    
    if "access_token" in res_json:
        # Cache for 50 minutes (3000 seconds) to be safe (PhonePe standard is 60 minutes)
        OAUTH_TOKEN_CACHE["token"] = res_json["access_token"]
        OAUTH_TOKEN_CACHE["expires_at"] = now + 3000
        return res_json["access_token"]
    else:
        raise Exception(f"OAuth Token Generation failed: {res_json.get('error_description', 'Unknown Error')}")

async def _phonepe_initiate_real(booking_id: str, amount_rupees: int, phone: str):
    env = os.environ.get("PHONEPE_ENV", "sandbox")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    
    merchant_id = os.environ.get("PHONEPE_MERCHANT_ID")
    salt_key = os.environ.get("PHONEPE_SALT_KEY")
    salt_index = os.environ.get("PHONEPE_SALT_INDEX", "1")

    # If V1 credentials (Merchant ID & Salt Key) are provided, use PhonePe V1 SHA256 API
    if merchant_id and salt_key:
        import base64, hashlib, json, asyncio
        amount_paise = int(amount_rupees * 100)
        payload_dict = {
            "merchantId": merchant_id,
            "merchantTransactionId": booking_id.replace("-", ""),
            "merchantUserId": "MUID" + booking_id[:8].replace("-", ""),
            "amount": amount_paise,
            "redirectUrl": f"{frontend_url}/token/{booking_id}",
            "redirectMode": "REDIRECT",
            "callbackUrl": f"{frontend_url}/token/{booking_id}",
            "paymentInstrument": {"type": "PAY_PAGE"}
        }
        json_bytes = json.dumps(payload_dict).encode("utf-8")
        base64_payload = base64.b64encode(json_bytes).decode("utf-8")
        string_to_hash = base64_payload + "/pg/v1/pay" + salt_key
        sha256_hash = hashlib.sha256(string_to_hash.encode("utf-8")).hexdigest()
        x_verify = f"{sha256_hash}###{salt_index}"
        
        url = "https://api.phonepe.com/apis/hermes/pg/v1/pay" if env == "production" else "https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/pay"
        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": x_verify
        }
        try:
            response = await asyncio.to_thread(requests.post, url, json={"request": base64_payload}, headers=headers, timeout=10)
            res_data = response.json()
            if res_data.get("success") and "url" in res_data.get("data", {}).get("instrumentResponse", {}).get("redirectInfo", {}):
                return res_data["data"]["instrumentResponse"]["redirectInfo"]["url"]
            elif "redirectUrl" in res_data:
                return res_data["redirectUrl"]
        except Exception as e:
            logger.error(f"PhonePe V1 initiation failed: {e}")

    # PhonePe V2 OAuth API
    token = await _get_oauth_token()
    amount_paise = int(amount_rupees * 100)
    
    payload = {
        "merchantOrderId": booking_id.replace("-", ""),
        "amount": amount_paise,
        "paymentFlow": {
            "type": "PG_CHECKOUT",
            "merchantUrls": {
                "redirectUrl": f"{frontend_url}/token/{booking_id}"
            }
        }
    }
    
    if env == "production":
        url = "https://api.phonepe.com/apis/pg/checkout/v2/pay"
    else:
        url = "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay"
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"O-Bearer {token}"
    }
    
    try:
        import asyncio
        response = await asyncio.to_thread(requests.post, url, json=payload, headers=headers, timeout=10)
        res_data = response.json()
    except Exception as e:
        raise HTTPException(500, f"Failed to connect to PhonePe: {str(e)}")
        
    if "redirectUrl" in res_data:
        return res_data["redirectUrl"]
    elif res_data.get("success") and "redirectUrl" in res_data.get("data", {}):
        return res_data["data"]["redirectUrl"]
    else:
        raise HTTPException(400, f"PhonePe API Error: {res_data.get('message', 'Unknown Error')}")

@api_router.post("/payment/phonepe/initiate")
async def phonepe_initiate(payload: PaymentInitiateRequest):
    doc = await db.bookings.find_one({"id": payload.booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Booking not found")
        
    await db.bookings.update_one({"id": payload.booking_id}, {"$set": {"payment_provider": "phonepe"}})
    
    merchant_id = os.environ.get("PHONEPE_MERCHANT_ID") or os.environ.get("PHONEPE_CLIENT_ID")
    salt_key = os.environ.get("PHONEPE_SALT_KEY") or os.environ.get("PHONEPE_CLIENT_SECRET")
    
    if not merchant_id or not salt_key:
        raise HTTPException(400, "PhonePe credentials are not configured in environment variables.")
        
    checkout_url = await _phonepe_initiate_real(payload.booking_id, doc["price"], doc["phone"])
    return {
        "success": True,
        "checkout_url": checkout_url,
        "merchant_order_id": payload.booking_id,
        "amount": doc["price"],
        "provider": "phonepe",
        "mocked": False,
    }

@api_router.post("/payment/phonepe/callback")
async def phonepe_callback(payload: PaymentInitiateRequest):
    return await _payment_callback(payload.booking_id)

@api_router.post("/payment/gpay/initiate")
async def gpay_initiate(payload: PaymentInitiateRequest):
    return await phonepe_initiate(payload)

@api_router.post("/payment/gpay/callback")
async def gpay_callback(payload: PaymentInitiateRequest):
    return await _payment_callback(payload.booking_id)

async def verify_phonepe_payment_status(booking_id: str) -> bool:
    client_id = os.environ.get("PHONEPE_CLIENT_ID")
    client_secret = os.environ.get("PHONEPE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return False
        
    try:
        token = await _get_oauth_token()
        sanitized_id = booking_id.replace("-", "")
        env = os.environ.get("PHONEPE_ENV", "sandbox")
        if env == "production":
            url = f"https://api.phonepe.com/apis/pg/checkout/v2/order/{sanitized_id}/status"
        else:
            url = f"https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/order/{sanitized_id}/status"
            
        headers = {
            "Authorization": f"O-Bearer {token}"
        }
        import requests, asyncio
        res = await asyncio.to_thread(requests.get, url, headers=headers, timeout=5)
        if res.status_code == 200:
            res_data = res.json()
            state = extract_phonepe_state(res_data)
            return state == "COMPLETED"
    except Exception as e:
        logger.error(f"Error checking PhonePe payment status for verification: {e}")
    return False

async def ensure_booking_token(doc: dict) -> dict:
    if not doc:
        return doc
    booking_id = doc.get("id")
    token = str(doc.get("token", ""))
    payment_status = doc.get("payment_status", "")
    payment_method = doc.get("payment_method", "")
    
    # If token already starts with T-, it's valid
    if token.startswith("T-"):
        return doc
        
    # Strictly ONLY generate token if payment is paid OR cash
    if payment_status == "paid" or payment_method == "cash":
        try:
            new_token = await generate_daily_token()
        except Exception as ex:
            import time
            new_token = f"T-00{int(time.time()) % 100}"
            
        await db.bookings.update_one(
            {"id": booking_id},
            {"$set": {
                "token": new_token,
                "payment_status": "paid",
                "status": "queued"
            }}
        )
        doc["token"] = new_token
        doc["payment_status"] = "paid"
        doc["status"] = "queued"
    return doc

async def _payment_callback(booking_id: str, skip_verify: bool = False):
    doc = await db.bookings.find_one({"id": booking_id})
    if not doc:
        raise HTTPException(404, "Booking not found")

    if not skip_verify and is_phonepe_production():
        try:
            is_valid = await verify_phonepe_payment_status(booking_id)
            if not is_valid:
                # Mark as failed in DB and DO NOT generate token!
                await db.bookings.update_one(
                    {"id": booking_id},
                    {"$set": {"payment_status": "failed", "status": "failed"}}
                )
                doc["payment_status"] = "failed"
                doc["status"] = "failed"
                raise HTTPException(400, "Payment failed or cancelled on PhonePe")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Verification check error for {booking_id}: {e}")

    # Mark as paid and generate token strictly on success
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {"payment_status": "paid", "status": "queued"}}
    )
    doc["payment_status"] = "paid"
    doc["status"] = "queued"

    updated_doc = await ensure_booking_token(doc)
    return {"success": True, "booking": updated_doc}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def background_payment_sync_loop():
    import asyncio
    logger.info("Starting background PhonePe payment sync loop (3s interval)...")
    while True:
        try:
            cursor_pending = db.bookings.find(
                {
                    "payment_method": "online",
                    "payment_status": "pending"
                }
            )
            all_pending = await cursor_pending.to_list(100)
            for b in all_pending:
                booking_id = b["id"]
                try:
                    is_valid = await verify_phonepe_payment_status(booking_id)
                    if is_valid:
                        logger.info(f"[Auto Sync Loop] Payment verified for {booking_id}. Generating token...")
                        await _payment_callback(booking_id)
                except Exception as ex:
                    logger.error(f"[Auto Sync Loop] Error verifying {booking_id}: {ex}")
        except Exception as e:
            logger.error(f"[Auto Sync Loop] Loop error: {e}")
        await asyncio.sleep(3)


@app.on_event("startup")
async def startup_event():
    await init_config()
    await init_services()
    import asyncio
    asyncio.create_task(background_payment_sync_loop())
    await migrate_legacy_bookings()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
