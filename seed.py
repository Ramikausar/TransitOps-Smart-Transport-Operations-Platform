from datetime import date, datetime, timedelta
import random
from app.extensions import db
from app.models import User, Role, Permission, role_permissions, Company, SystemSetting, Vehicle, VehicleType, FuelType, VehicleDocument, Driver, DriverDocument, Trip, TripHistory, Maintenance, MaintenanceType, FuelLog, Expense, ExpenseCategory, Notification, ActivityLog, AuditLog

def seed_database():
    print("Initializing Database Seed (15 Vehicles, 10 Drivers, Clean Transactions slate)...")
    
    # 1. Recreate tables
    db.drop_all()
    db.create_all()
    
    # 2. Seed Permissions
    permissions_list = [
        ("manage_fleet", "Create, read, update, delete fleet vehicles"),
        ("manage_drivers", "Manage driver personnel records and documents"),
        ("manage_trips", "Dispatch, create, and close trip registers"),
        ("manage_maintenance", "Schedule and approve maintenance orders"),
        ("manage_fuel", "Log fuel purchases and track metrics"),
        ("manage_expenses", "Access ledger entries and operational costs"),
        ("view_reports", "Generate CSV and ReportLab PDF documents"),
        ("manage_settings", "Modify portal profiles and user authorization")
    ]
    perms = {}
    for name, desc in permissions_list:
        p = Permission(name=name, description=desc)
        db.session.add(p)
        perms[name] = p
    db.session.flush()
    
    # 3. Seed Roles
    roles_data = [
        {"name": "Administrator", "desc": "Full root-level configurations access", "perms": list(perms.values())},
        {"name": "Fleet Manager", "desc": "Fleet routing, drivers, and maintenance logs", "perms": [perms["manage_fleet"], perms["manage_drivers"], perms["manage_trips"], perms["manage_maintenance"], perms["manage_fuel"], perms["manage_expenses"], perms["view_reports"]]},
        {"name": "Safety Officer", "desc": "License compliance verification, documents, and records", "perms": [perms["manage_drivers"], perms["manage_maintenance"]]},
        {"name": "Financial Analyst", "desc": "General expense bookkeeping and reports download", "perms": [perms["manage_fuel"], perms["manage_expenses"], perms["view_reports"]]},
        {"name": "Driver", "desc": "Logistics operations driver portal access", "perms": []}
    ]
    roles = {}
    for r_data in roles_data:
        r = Role(name=r_data["name"], description=r_data["desc"])
        r.permissions = r_data["perms"]
        db.session.add(r)
        roles[r_data["name"]] = r
    db.session.flush()
    
    # 4. Seed Company & System Settings
    comp = Company(
        name="TransitOps Logistics India Pvt. Ltd.",
        address="102, GIDC Electronic Estate, Sector 26, Gandhinagar, Gujarat - 382028",
        phone="+91 79 23214567",
        email="info@transitops.in",
        tax_id="24AAACT8890C1Z5", # GSTIN
        currency="₹"
    )
    db.session.add(comp)
    
    settings = [
        ("site_name", "TransitOps ERP", "System branding header title"),
        ("alert_threshold_days", "30", "Days before license/RC expiry to notify Safety Officer"),
        ("allow_overloading", "False", "Enforce cargo limit strict validation")
    ]
    for k, v, d in settings:
        db.session.add(SystemSetting(key=k, value=v, description=d))
    db.session.flush()
    
    # 5. Seed Users
    # 5.1 Admin and Staff logins
    staff_users = [
        ("admin@transitops.com", "System Administrator", "Administrator"),
        ("manager@transitops.com", "Amit Patel", "Fleet Manager"),
        ("safety@transitops.com", "Deepak Singh", "Safety Officer"),
        ("finance@transitops.com", "Rajesh Kumar", "Financial Analyst")
    ]
    for email, name, role_name in staff_users:
        u = User(email=email, name=name, role_id=roles[role_name].id, is_active=True)
        u.set_password("transitops123")
        db.session.add(u)
    
    # 5.2 Seeding 10 Driver user profiles
    driver_first = ["Rahul", "Amit", "Rajesh", "Deepak", "Mohit", "Arjun", "Sanjay", "Vikram", "Nitin", "Rakesh", "Harsh", "Jayesh", "Karan", "Manish", "Suresh"]
    driver_last = ["Sharma", "Patel", "Kumar", "Singh", "Verma", "Chauhan", "Yadav", "Solanki", "Joshi", "Meena", "Parmar"]
    
    driver_emails = [f"driver{i}@transitops.com" for i in range(1, 11)]
    driver_names = []
    # Guarantee 10 unique driver names
    random.seed(42)
    while len(driver_names) < 10:
        name = f"{random.choice(driver_first)} {random.choice(driver_last)}"
        if name not in driver_names:
            driver_names.append(name)
            
    driver_users = []
    for i in range(10):
        email = driver_emails[i]
        name = driver_names[i]
        u = User(email=email, name=name, role_id=roles["Driver"].id, is_active=True)
        u.set_password("transitops123")
        db.session.add(u)
        driver_users.append(u)
    db.session.flush()
    
    # 6. Seed Vehicle Types & Fuel Types
    v_types = ["Truck", "Van", "Flatbed", "Refrigerated Truck", "Bus", "Car"]
    vt_objs = {}
    for t in v_types:
        vt = VehicleType(name=t, description=f"{t} category asset")
        db.session.add(vt)
        vt_objs[t] = vt
        
    f_types = ["Petrol", "Diesel", "CNG", "EV"]
    ft_objs = {}
    for f in f_types:
        ft = FuelType(name=f)
        db.session.add(ft)
        ft_objs[f] = ft
    db.session.flush()
    
    # 7. Seed Expense Categories & Maintenance Types
    exp_cats = ["Fuel", "Repair", "Insurance", "FASTag", "Toll Tax", "Parking", "Miscellaneous"]
    cat_objs = {}
    for c in exp_cats:
        cat = ExpenseCategory(name=c, description=f"{c} expense ledger classification")
        db.session.add(cat)
        cat_objs[c] = cat
        
    m_types = ["Oil Change", "Tyre", "Battery", "General Service", "Accident Repair"]
    mt_objs = {}
    for m in m_types:
        mt = MaintenanceType(name=m, description=f"Maintenance for {m}")
        db.session.add(mt)
        mt_objs[m] = mt
    db.session.flush()
    
    # 8. Seed 15 Vehicles (Indian RTO Registrations)
    states = ["GJ", "MH", "DL", "RJ", "UP", "KA", "HR", "AP", "TS", "TN"]
    brand_models = {
        "Truck": [("Tata Signa 4825", 25000), ("Ashok Leyland U-4019", 20000), ("BharatBenz 2823C", 18000)],
        "Van": [("Tata Winger", 3000), ("Mahindra Supro", 2000), ("Force Traveller", 4000)],
        "Flatbed": [("Tata LPT 1613", 16000), ("Ashok Leyland Ecomet", 14000)],
        "Refrigerated Truck": [("BharatBenz 1923R Reefer", 15000), ("Tata Ultra Reefer", 10000)],
        "Bus": [("Tata Starbus", 8000), ("Ashok Leyland Oyster", 6000)],
        "Car": [("Maruti Super Carry", 1200), ("Mahindra Bolero Pickup", 1700)]
    }
    
    vehicles = []
    reg_counter = 1001
    today = date.today()
    
    for i in range(15):
        v_type_name = random.choice(list(brand_models.keys()))
        brand, capacity = random.choice(brand_models[v_type_name])
        
        state = random.choice(states)
        district = random.randint(1, 35)
        letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        reg_no = f"{state}{str(district).zfill(2)}{letters}{reg_counter}"
        reg_counter += 1
        
        # distribute fuel types
        if v_type_name == "Truck" or v_type_name == "Flatbed" or v_type_name == "Refrigerated Truck":
            fuel = "Diesel"
        elif v_type_name == "Van" or v_type_name == "Car":
            fuel = random.choice(["Diesel", "Petrol", "CNG", "EV"])
        else:
            fuel = random.choice(["Diesel", "CNG"])
            
        vehicle = Vehicle(
            registration_number=reg_no,
            name=brand,
            model=f"{brand} V2",
            vehicle_type_id=vt_objs[v_type_name].id,
            max_load_capacity=float(capacity),
            current_odometer=0.0,
            purchase_date=today - timedelta(days=random.randint(100, 1800)),
            acquisition_cost=float(random.randint(800000, 4500000)),
            insurance_expiry=today + timedelta(days=random.randint(30, 300)), # Keep active
            rc_expiry=today + timedelta(days=random.randint(120, 1200)),
            status="available", # Initialize all to available
            fuel_type_id=ft_objs[fuel].id
        )
        db.session.add(vehicle)
        vehicles.append(vehicle)
        
        # Seed 1 document for each vehicle
        doc = VehicleDocument(
            vehicle=vehicle,
            document_name="Registration Certificate (RC)",
            document_type="RC",
            expiry_date=vehicle.rc_expiry
        )
        db.session.add(doc)
        
    db.session.flush()
    
    # 9. Seed 10 Drivers (Link each to a Driver User)
    drivers = []
    license_counter = 10001
    
    for i in range(10):
        user = driver_users[i]
        expiry_days = random.randint(30, 700) # Keep active
        license_no = f"DL-{random.choice(states)}2023{license_counter}"
        license_counter += 1
        
        driver = Driver(
            name=user.name,
            license_number=license_no,
            license_category=random.choice(["LMV", "HMV", "TRANS", "HAZ"]),
            license_expiry=today + timedelta(days=expiry_days),
            phone=f"+91 {random.randint(7000000000, 9999999999)}",
            email=user.email,
            address=f"Flat {random.randint(1,500)}, Logistics Colony, Sector {random.randint(1,20)}, {random.choice(driver_first)} City",
            emergency_contact_name=f"{random.choice(driver_first)} {random.choice(driver_last)}",
            emergency_contact_phone=f"+91 {random.randint(7000000000, 9999999999)}",
            safety_score=float(random.randint(85, 100)), # Seed good score
            joining_date=today - timedelta(days=random.randint(30, 700)),
            status="available", # Initialize all to available
            user_id=user.id
        )
        db.session.add(driver)
        drivers.append(driver)
        
        # Add Driver License Doc
        doc = DriverDocument(
            driver=driver,
            document_name="Driving License",
            document_type="License",
            expiry_date=driver.license_expiry
        )
        db.session.add(doc)
        
    db.session.flush()
    
    # 10. Seed 0 Trips, 0 Fuel Logs, 0 Expenses, 0 Maintenance logs as requested (Manual control slate)
    
    db.session.commit()
    print("Database fully reset! Seeded 15 Vehicles and 10 Drivers in Available status. Trips, Fuel and Expenses tables cleared.")

if __name__ == "__main__":
    from flask import Flask
    from config import Config
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        seed_database()
