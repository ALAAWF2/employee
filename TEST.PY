# -*- coding: utf-8 -*-
"""
converter_employees_v3_with_monthly_data.py
إعداد: علاء وفائي 🟧
الغرض: تحويل بيانات الموظفين والفروع إلى ملف JSON متكامل
        مع قراءة المبيعات والعمولات الشهرية وحساب متوسط الدخل الشهري بدقة.
"""

import pandas as pd
import json
import numpy as np
from datetime import datetime

# ===== إعدادات الملفات =====
EMP_FILE = "emp.csv"
BRANCHES_FILE = "branches.csv"
OUTPUT_FILE = "data.json"
ENCODING = "windows-1256"

# =====================================================
def normalize_name(name: str):
    """توحيد شكل الأسماء لتفادي الاختلافات البسيطة"""
    if not isinstance(name, str):
        return ""
    return (
        name.strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace("\\", " ")
        .replace("/", " ")
        .replace("  ", " ")
    )

# =====================================================
def calculate_years_of_service(join_date_str: str):
    """تحسب سنوات الخدمة بصيغة مثل '5 و 6 شهور'"""
    try:
        join_date = pd.to_datetime(join_date_str, errors="coerce")
        if pd.isna(join_date):
            return "0"
        today = pd.Timestamp.today()
        diff = today - join_date
        years = diff.days // 365
        months = (diff.days % 365) // 30

        if years == 0 and months == 0:
            return "أقل من شهر"
        if years == 0:
            return f"{months} شهور"
        if months == 0:
            return f"{years}"
        return f"{years} و {months} شهور"
    except Exception:
        return "0"

# =====================================================
def safe_float(value):
    """تحويل القيم الرقمية بأمان مع تنظيف الرموز والفواصل"""
    try:
        if value in [None, "", "nan", "NaN", "None"]:
            return 0.0
        value = str(value).replace(",", "").replace("٫", ".").strip()
        return float(value)
    except:
        return 0.0

# =====================================================
def clean_data(obj):
    """تنظيف القيم غير الصالحة داخل dict أو list"""
    if isinstance(obj, dict):
        return {k: clean_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_data(v) for v in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return 0
        return obj
    elif obj in [None, "NaN", "nan", "None"]:
        return 0
    return obj

# =====================================================
def process():
    try:
        print("📥 قراءة ملفات CSV...")
        emp_df = pd.read_csv(EMP_FILE, encoding=ENCODING)
        branches_df = pd.read_csv(BRANCHES_FILE, encoding=ENCODING)

        emp_df.columns = emp_df.columns.str.strip()
        branches_df.columns = branches_df.columns.str.strip()

        # ===== معالجة بيانات المدراء =====
        print("🧭 معالجة بيانات المدراء...")
        managers_map = {}
        for _, row in branches_df.iterrows():
            manager = str(row.get("AREA MANAGER", "")).strip()
            branch = str(row.get("BRANCH", "")).strip()
            if not manager or not branch:
                continue
            managers_map.setdefault(manager, []).append(branch)

        # ===== معالجة بيانات الموظفين =====
        print("👷 معالجة بيانات الموظفين...")
        employees_by_store = {}
        total_employees = 0

        for _, row in emp_df.iterrows():
            outlet_raw = str(row.get("outlet name", "")).strip()
            if not outlet_raw:
                continue

            normalized_outlet = normalize_name(outlet_raw)
            if normalized_outlet not in employees_by_store:
                employees_by_store[normalized_outlet] = {
                    "original_name": outlet_raw,
                    "employees": []
                }

            emp_id = row.get("الرقم الوظيفي", "")
            name = str(row.get("name", "")).strip()
            title = str(row.get("المسمى الوظيفي", "")).strip()
            join_date = str(row.get("join date", "")).strip()
            years_of_service = calculate_years_of_service(join_date)

            total_sales = safe_float(row.get("total sales", 0))
            salary = safe_float(row.get("salary", 0))
            total_commission = safe_float(row.get("total commission", 0))

            # المبيعات والعمولات الشهرية (sales-1..sales-9 , commission-1..commission-9)
            monthly_sales = [safe_float(row.get(f"sales-{i}", 0)) for i in range(1, 12)]
            monthly_commissions = [safe_float(row.get(f"commission-{i}", 0)) for i in range(1, 12)]


            # حساب متوسط العمولات الشهرية الفعّالة فقط
            months_count = max(len([v for v in monthly_commissions if v > 0]), 1)
            avg_monthly_comm = sum(monthly_commissions) / months_count
            average_income = salary + avg_monthly_comm

            # البحث عن المدير بناءً على المعرض
            manager_name = ""
            for m_name, stores in managers_map.items():
                if outlet_raw in stores:
                    manager_name = m_name
                    break

            employees_by_store[normalized_outlet]["employees"].append({
                "id": emp_id,
                "name": name,
                "title": title,
                "outlet": outlet_raw,
                "manager": manager_name,
                "join_date": join_date,
                "years_of_service": years_of_service,
                "salary": salary,
                "total_commission": total_commission,
                "total_sales": total_sales,
                "monthly_sales": monthly_sales,
                "monthly_commissions": monthly_commissions,
                "average_income": average_income
            })
            total_employees += 1

        final_data = {
            "managers": managers_map,
            "employees_by_store": employees_by_store
        }

        # تنظيف القيم قبل الحفظ
        final_data = clean_data(final_data)

        # ===== حفظ البيانات =====
        print("💾 حفظ البيانات إلى JSON...")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)

        print(f"\n✅ تم إنشاء الملف '{OUTPUT_FILE}' بنجاح!")
        print(f"👥 عدد الموظفين الكلي: {total_employees}")
        print(f"🏢 عدد المعارض: {len(employees_by_store)}")

    except FileNotFoundError as e:
        print(f"❌ الملف غير موجود: {e.filename}")
    except Exception as e:
        print(f"⚠️ خطأ غير متوقع: {e}")

# =====================================================
if __name__ == "__main__":
    process()
