from flask import render_template, redirect, url_for, flash, request, send_file, abort
from flask_login import login_required
from app.reports import reports_bp
from app.models import Vehicle, Driver, Trip, Maintenance, FuelLog, Expense, ExpenseCategory
from app.extensions import db
from app.utils.decorators import role_required
from datetime import datetime, date, timedelta
from io import BytesIO, StringIO
import csv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

@reports_bp.route('/')
@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def index():
    return render_template('reports/index.html')

@reports_bp.route('/view')
@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def view_report():
    report_type = request.args.get('type', 'fleet_costs')
    headers, rows, title = generate_report_data(report_type)
    
    return render_template(
        'reports/view.html',
        report_type=report_type,
        headers=headers,
        rows=rows,
        title=title
    )

@reports_bp.route('/export')
@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def export_report():
    report_type = request.args.get('type', 'fleet_costs')
    export_format = request.args.get('format', 'csv')
    
    headers, rows, title = generate_report_data(report_type)
    
    if export_format == 'csv':
        si = StringIO()
        # Ensure utf-8 encoding and include signature
        cw = csv.writer(si)
        cw.writerow([title])
        cw.writerow([f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"])
        cw.writerow([])
        cw.writerow(headers)
        cw.writerows(rows)
        
        output = BytesIO()
        output.write(si.getvalue().encode('utf-8'))
        output.seek(0)
        
        filename = f"{report_type}_{date.today().strftime('%d-%m-%Y')}.csv"
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    elif export_format == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter, 
            rightMargin=36, 
            leftMargin=36, 
            topMargin=36, 
            bottomMargin=36
        )
        story = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=10
        )
        meta_style = ParagraphStyle(
            'ReportMeta',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=20
        )
        
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')} | TransitOps ERP", meta_style))
        story.append(Spacer(1, 10))
        
        table_data = [headers]
        for row in rows:
            table_data.append([str(v) for v in row])
            
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('BOTTOMPADDING', (0,1), (-1,-1), 5),
            ('TOPPADDING', (0,1), (-1,-1), 5),
        ]))
        
        story.append(t)
        doc.build(story)
        buffer.seek(0)
        
        filename = f"{report_type}_{date.today().strftime('%d-%m-%Y')}.pdf"
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    else:
        abort(400)

def generate_report_data(report_type):
    if report_type == 'fleet_costs':
        title = "Vehicle Operating Costs & Usage Report"
        headers = ["Reg Number", "Name", "Type", "Status", "Odometer (KM)", "Fuel Costs (₹)", "Repair Costs (₹)", "Other Expenses (₹)", "Total Cost (₹)"]
        
        vehicles = Vehicle.query.all()
        rows = []
        for v in vehicles:
            fuel = sum(e.amount for e in v.expenses if e.expense_type == 'Fuel')
            repair = sum(e.amount for e in v.expenses if e.expense_type == 'Repair')
            others = sum(e.amount for e in v.expenses if e.expense_type not in ['Fuel', 'Repair'])
            total = sum(e.amount for e in v.expenses)
            rows.append([
                v.registration_number,
                v.name,
                v.type,
                v.status.title(),
                f"{v.current_odometer:,.1f}",
                f"{fuel:,.2f}",
                f"{repair:,.2f}",
                f"{others:,.2f}",
                f"{total:,.2f}"
            ])
            
    elif report_type == 'fuel_efficiency':
        title = "Vehicle Fuel Efficiency & Cost Report"
        headers = ["Reg Number", "Name", "Type", "Total Distance (KM)", "Total Fuel (Litres)", "Efficiency (KM/L)", "Total Fuel Cost (₹)"]
        
        vehicles = Vehicle.query.all()
        rows = []
        for v in vehicles:
            completed_trips = [t for t in v.trips if t.status == 'completed']
            total_dist = sum(t.distance for t in completed_trips)
            total_fuel = sum(t.fuel_consumed for t in completed_trips if t.fuel_consumed is not None)
            efficiency = round(total_dist / total_fuel, 2) if total_fuel > 0 else 0.0
            fuel_cost = sum(e.amount for e in v.expenses if e.expense_type == 'Fuel')
            
            rows.append([
                v.registration_number,
                v.name,
                v.type,
                f"{total_dist:,.1f}",
                f"{total_fuel:,.1f}",
                f"{efficiency:,.2f}",
                f"{fuel_cost:,.2f}"
            ])
            
    elif report_type == 'driver_performance':
        title = "Driver Performance & Safety Audit Report"
        headers = ["Driver Name", "License No", "Safety Score", "Joined Date", "Status", "Completed Trips", "Total Distance (KM)"]
        
        drivers = Driver.query.all()
        rows = []
        for d in drivers:
            completed_trips = [t for t in d.trips if t.status == 'completed']
            total_dist = sum(t.distance for t in completed_trips)
            
            rows.append([
                d.name,
                d.license_number,
                f"{d.safety_score:.1f}",
                d.joining_date.strftime('%d-%m-%Y'),
                d.status.title(),
                len(completed_trips),
                f"{total_dist:,.1f}"
            ])
            
    elif report_type == 'licenses':
        title = "Upcoming Driver License Expiries"
        headers = ["Driver Name", "License Number", "License Category", "Expiry Date", "Days Remaining", "Status"]
        
        drivers = Driver.query.order_by(Driver.license_expiry.asc()).all()
        rows = []
        today = date.today()
        for d in drivers:
            remaining = (d.license_expiry - today).days
            status = "Expired" if remaining < 0 else ("Urgent" if remaining <= 30 else "Valid")
            rows.append([
                d.name,
                d.license_number,
                d.license_category,
                d.license_expiry.strftime('%d-%m-%Y'),
                remaining,
                status
            ])
            
    elif report_type == 'maintenance':
        title = "Maintenance Operations & Repair Summary"
        headers = ["Reg Number", "Type", "Description", "Start Date", "End Date", "Cost (₹)", "Status"]
        
        logs = Maintenance.query.join(Vehicle).order_by(Maintenance.start_date.desc()).all()
        rows = []
        for l in logs:
            rows.append([
                l.vehicle.registration_number,
                l.type,
                l.description,
                l.start_date.strftime('%d-%m-%Y'),
                l.end_date.strftime('%d-%m-%Y'),
                f"{l.cost:,.2f}",
                l.status.title()
            ])
            
    else:
        title = "Operations Report"
        headers = []
        rows = []
        
    return headers, rows, title
