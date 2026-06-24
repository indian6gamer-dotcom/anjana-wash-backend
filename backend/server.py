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
    from backend.postgres_db import PostgresDB
    db = PostgresDB(DATABASE_URL)
else:
    from backend.sqlite_db import SQLiteDB
    db = SQLiteDB(str(ROOT_DIR / 'anjana_clean.db'))
client = db

app = FastAPI(title="Anjana Wash API")
api_router = APIRouter(prefix="/api")

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
        {"id": "xuv", "label": "XUV / SUV", "icon": "Car"},
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


class Booking(BaseModel):
    id: str
    token: str
    customer_name: str
    phone: str
    vehicle_number: str
    vehicle_photo: str
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


class CompleteBookingRequest(BaseModel):
    worker_photo: Optional[str] = None  # required if cash


class PinRequest(BaseModel):
    role: str  # "worker" or "owner"
    pin: str


class UpdatePinRequest(BaseModel):
    owner_pin: str  # for auth
    role: str  # "worker" or "owner"
    new_pin: str


class PaymentInitiateRequest(BaseModel):
    booking_id: str


# ---------- Helpers ----------
async def get_service_doc(service_id: str):
    doc = await db.services.find_one({"id": service_id, "active": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or inactive service")
    return doc


async def verify_owner_pin_or_raise(pin: str):
    cfg = await db.config.find_one({"_id": "pins"}, {"_id": 0})
    if not cfg or cfg.get("owner_pin") != pin:
        raise HTTPException(403, "Invalid owner PIN")


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
    existing = await db.config.find_one({"_id": "pins"}, {"_id": 0})
    if not existing:
        await db.config.insert_one({"_id": "pins", "worker_pin": "1234", "owner_pin": "9999"})


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


@api_router.get("/services/by-category/{category_id}", response_model=List[Service])
async def services_by_category(category_id: str):
    if category_id not in LEAF_BY_ID:
        raise HTTPException(400, "Invalid category")
    cursor = db.services.find({"category_id": category_id, "active": True}, {"_id": 0}).sort("price", 1)
    return await cursor.to_list(100)


@api_router.get("/owner/services", response_model=List[Service])
async def owner_list_services():
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
    doc = await db.services.find_one({"id": service_id}, {"_id": 0})
    return doc


@api_router.delete("/owner/services/{service_id}")
async def owner_delete_service(service_id: str, payload: ServiceDelete):
    await verify_owner_pin_or_raise(payload.owner_pin)
    res = await db.services.delete_one({"id": service_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Service not found")
    return {"success": True}


@api_router.post("/bookings", response_model=Booking)
async def create_booking(payload: BookingCreate):
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
    token = await generate_daily_token()
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
        status="queued",
        worker_photo=payload.worker_photo,
        created_at=now_ist_iso(),
    )
    doc = booking.model_dump()
    await db.bookings.insert_one(doc)
    return booking


@api_router.get("/bookings/queue", response_model=List[Booking])
async def queue():
    # only queued bookings where online is paid, or cash (which is allowed in queue)
    cursor = db.bookings.find(
        {"status": "queued", "$or": [{"payment_method": "cash"}, {"payment_status": "paid"}]},
        {"_id": 0},
    ).sort("created_at", 1)
    return await cursor.to_list(500)


@api_router.get("/bookings", response_model=List[Booking])
async def all_bookings(date: Optional[str] = None):
    q = {}
    if date:
        q["created_at"] = {"$regex": f"^{date}"}
    cursor = db.bookings.find(q, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(1000)


@api_router.get("/bookings/{booking_id}", response_model=Booking)
async def get_booking(booking_id: str):
    doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Booking not found")
        
    # Auto-check status if online phonepe and pending
    if doc.get("payment_method") == "online" and doc.get("payment_provider") == "phonepe" and doc.get("payment_status") == "pending":
        client_id = os.environ.get("PHONEPE_CLIENT_ID")
        client_secret = os.environ.get("PHONEPE_CLIENT_SECRET")
        if client_id and client_secret:
            try:
                token = _get_oauth_token()
                env = os.environ.get("PHONEPE_ENV", "sandbox")
                
                sanitized_id = booking_id.replace("-", "")
                if env == "production":
                    url = f"https://api.phonepe.com/apis/pg/checkout/v2/order/{sanitized_id}/status"
                else:
                    url = f"https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/order/{sanitized_id}/status"
                    
                headers = {
                    "Authorization": f"O-Bearer {token}"
                }
                
                res = requests.get(url, headers=headers, timeout=5)
                res_data = res.json()
                
                # Check status: PhonePe V2 status is typically in res_data.get("state")
                state = res_data.get("state") or res_data.get("status")
                if state == "COMPLETED":
                    await db.bookings.update_one({"id": booking_id}, {"$set": {"payment_status": "paid"}})
                    doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
            except Exception as e:
                logger.error(f"Error auto-checking PhonePe status for booking {booking_id}: {str(e)}")
                
    return doc


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


@api_router.get("/bookings/stats/today")
async def today_stats():
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
    cfg = await db.config.find_one({"_id": "pins"}, {"_id": 0})
    if not cfg:
        await init_config()
        cfg = await db.config.find_one({"_id": "pins"}, {"_id": 0})
    key = f"{payload.role}_pin"
    if key not in cfg:
        raise HTTPException(400, "Invalid role")
    return {"success": cfg[key] == payload.pin}


@api_router.post("/auth/update-pin")
async def update_pin(payload: UpdatePinRequest):
    cfg = await db.config.find_one({"_id": "pins"}, {"_id": 0})
    if not cfg or cfg.get("owner_pin") != payload.owner_pin:
        raise HTTPException(403, "Invalid owner PIN")
    if payload.role not in ("worker", "owner"):
        raise HTTPException(400, "Invalid role")
    if not (payload.new_pin.isdigit() and 4 <= len(payload.new_pin) <= 6):
        raise HTTPException(400, "PIN must be 4-6 digits")
    await db.config.update_one(
        {"_id": "pins"},
        {"$set": {f"{payload.role}_pin": payload.new_pin}},
    )
    return {"success": True}


# ---------- PhonePe & GPay Payment Gateways ----------
import base64
import json
import requests
from fastapi import Request

def _get_oauth_token():
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
    
    response = requests.post(url, data=encoded_data, headers=headers, timeout=10)
    res_json = response.json()
    
    if "access_token" in res_json:
        return res_json["access_token"]
    else:
        raise Exception(f"OAuth Token Generation failed: {res_json.get('error_description', 'Unknown Error')}")

async def _phonepe_initiate_real(booking_id: str, amount_rupees: int, phone: str):
    env = os.environ.get("PHONEPE_ENV", "sandbox")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    
    token = _get_oauth_token()
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
        response = requests.post(url, json=payload, headers=headers, timeout=10)
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
    
    client_id = os.environ.get("PHONEPE_CLIENT_ID")
    client_secret = os.environ.get("PHONEPE_CLIENT_SECRET")
    
    if client_id and client_secret:
        checkout_url = await _phonepe_initiate_real(payload.booking_id, doc["price"], doc["phone"])
        return {
            "success": True,
            "checkout_url": checkout_url,
            "merchant_order_id": payload.booking_id,
            "amount": doc["price"],
            "provider": "phonepe",
            "mocked": False,
        }
    else:
        return {
            "success": True,
            "checkout_url": f"/phonepe-mock?booking_id={payload.booking_id}",
            "merchant_order_id": payload.booking_id,
            "amount": doc["price"],
            "provider": "phonepe",
            "mocked": True,
        }

@api_router.post("/payment/phonepe/callback")
async def phonepe_callback(payload: PaymentInitiateRequest):
    # Used for mock callbacks
    return await _payment_callback(payload.booking_id)

@api_router.post("/payment/gpay/initiate")
async def gpay_initiate(payload: PaymentInitiateRequest):
    return await _payment_initiate(payload.booking_id, provider="gpay")

@api_router.post("/payment/gpay/callback")
async def gpay_callback(payload: PaymentInitiateRequest):
    return await _payment_callback(payload.booking_id)

async def _payment_initiate(booking_id: str, provider: str):
    doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Booking not found")
    await db.bookings.update_one({"id": booking_id}, {"$set": {"payment_provider": provider}})
    mock_path = "/phonepe-mock" if provider == "phonepe" else "/gpay-mock"
    return {
        "success": True,
        "checkout_url": f"{mock_path}?booking_id={booking_id}",
        "merchant_order_id": booking_id,
        "amount": doc["price"],
        "provider": provider,
        "mocked": True,
    }

async def _payment_callback(booking_id: str):
    doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Booking not found")
    await db.bookings.update_one({"id": booking_id}, {"$set": {"payment_status": "paid"}})
    new_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    return {"success": True, "booking": new_doc}


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


@app.on_event("startup")
async def startup_event():
    await init_config()
    await init_services()
    await migrate_legacy_bookings()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
