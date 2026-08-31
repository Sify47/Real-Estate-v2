# api_scraper_final.py (النسخة المعدلة مع دعم dbt run)
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import json
import time
from datetime import datetime
import logging
import numpy as np
import uvicorn
from contextlib import asynccontextmanager
import subprocess  # لإضافة دعم تشغيل الأوامر
import shlex  # لمعالجة الأوامر بشكل آمن

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= دوال مساعدة للـ JSON =============

def convert_nan_to_none(obj):
    """تحويل قيم NaN و inf إلى None لتصبح صالحة للـ JSON"""
    if isinstance(obj, dict):
        return {key: convert_nan_to_none(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_nan_to_none(item) for item in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, pd.Series):
        return obj.apply(lambda x: None if pd.isna(x) else x).tolist()
    else:
        return obj

def dataframe_to_json_safe(df):
    """تحويل DataFrame إلى JSON مع التعامل مع NaN"""
    df_clean = df.replace({np.nan: None, np.inf: None, -np.inf: None})
    records = df_clean.to_dict(orient='records')
    
    cleaned_records = []
    for record in records:
        clean_record = {}
        for key, value in record.items():
            if isinstance(value, float):
                if np.isnan(value) or np.isinf(value):
                    clean_record[key] = None
                else:
                    clean_record[key] = value
            elif pd.isna(value):
                clean_record[key] = None
            else:
                clean_record[key] = value
        cleaned_records.append(clean_record)
    
    return cleaned_records

# ============= دوال السحب =============
def scrape_propertyfinder_page(page_url):
    """دالة لجمع البيانات من صفحة واحدة في PropertyFinder - نسخة محدثة"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

    try:
        response = requests.get(page_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        logger.error(f"خطأ في تحميل صفحة PropertyFinder {page_url}: {e}")
        return []

    def text_or_none(selector, parent):
        el = parent.select_one(selector)
        return el.get_text(strip=True) if el else None

    # ===== محاولة selectors متعددة =====
    property_cards = []
    
    # 1. محاولة الـ selectors الأكثر شيوعاً حالياً
    property_cards = soup.select("li[data-testid='property-card']")
    if not property_cards:
        property_cards = soup.select("div[data-testid='property-card']")
    if not property_cards:
        property_cards = soup.select("article[data-testid='property-card']")
    if not property_cards:
        property_cards = soup.select("li.styles-module_property-card__item__iI9g7")
    if not property_cards:
        property_cards = soup.select("div.styles-module_property-card__wrapper__X-0Hc")
    if not property_cards:
        # 2. البحث عن أي عنصر يحتوي على رابط عقار
        links = soup.select("a[href*='/en/property/']")
        if links:
            # جلب العناصر الأب للروابط
            property_cards = [link.find_parent() for link in links if link.find_parent()]
            # تصفية العناصر المكررة
            seen = set()
            unique_cards = []
            for card in property_cards:
                if card and id(card) not in seen:
                    seen.add(id(card))
                    unique_cards.append(card)
            property_cards = unique_cards
    
    # 3. إذا لم نجد شيئاً، جرب البحث عن div يحتوي على معلومات العقار
    if not property_cards:
        property_cards = soup.select("div.styles-module_property-card__content__P3f1F")
    
    logger.info(f"✅ تم العثور على {len(property_cards)} بطاقة عقار في الصفحة")
    
    # حفظ HTML للتصحيح (اختياري)
    if len(property_cards) == 0:
        with open(f"debug_page_{datetime.now().strftime('%H%M%S')}.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        logger.warning("⚠️ لم يتم العثور على عقارات - تم حفظ HTML للتصحيح")
    
    properties = []

    for card in property_cards:
        try:
            # ===== استخراج الرابط =====
            a = card.select_one("a[href*='/en/property/']")
            if not a:
                a = card.select_one("a.styles-module_property-card__link__ls66n")
            
            link = a.get('href') if a and a.get('href') else None
            if link and not link.startswith('http'):
                link = f"https://www.propertyfinder.eg{link}" if link.startswith('/') else link

            # ===== استخراج السعر =====
            price = None
            price_selectors = [
                "div.styles-module_content__price-area__QJek8",
                "div[data-testid='property-card-price']",
                "span.styles-module_property-card__price__XK2Qm",
                "div.styles-module_price__jvXkT"
            ]
            for selector in price_selectors:
                price_el = card.select_one(selector)
                if price_el:
                    price = price_el.get_text(strip=True)
                    break

            # ===== استخراج العنوان =====
            title = None
            title_selectors = [
                "h3.styles-module_content__title__pLLTh",
                "h3[data-testid='property-card-title']",
                "h3.styles-module_property-card__title__nvUzt",
                "h3"
            ]
            for selector in title_selectors:
                title_el = card.select_one(selector)
                if title_el:
                    title = title_el.get_text(strip=True)
                    break

            # ===== استخراج النوع =====
            type_ = None
            type_selectors = [
                "[data-testid='property-card-spec-propertyType']",
                "span.styles-module_property-card__property-type__YRI8T",
                "div.styles-module_specs__item__vLsLR"
            ]
            for selector in type_selectors:
                type_el = card.select_one(selector)
                if type_el:
                    type_ = type_el.get_text(strip=True)
                    break

            # ===== استخراج غرف النوم =====
            bedrooms = None
            bedroom_selectors = [
                "[data-testid='property-card-spec-bedroom']",
                "span[data-testid='bedrooms']",
                "span.styles-module_specs__bedrooms__mXz-1"
            ]
            for selector in bedroom_selectors:
                bed_el = card.select_one(selector)
                if bed_el:
                    bedrooms = bed_el.get_text(strip=True)
                    break

            # ===== استخراج الحمامات =====
            bathrooms = None
            bath_selectors = [
                "[data-testid='property-card-spec-bathroom']",
                "span[data-testid='bathrooms']"
            ]
            for selector in bath_selectors:
                bath_el = card.select_one(selector)
                if bath_el:
                    bathrooms = bath_el.get_text(strip=True)
                    break

            # ===== استخراج المساحة =====
            area = None
            area_selectors = [
                "[data-testid='property-card-spec-area']",
                "span[data-testid='area']"
            ]
            for selector in area_selectors:
                area_el = card.select_one(selector)
                if area_el:
                    area = area_el.get_text(strip=True)
                    break

            # ===== استخراج الموقع =====
            location = None
            location_selectors = [
                "p.styles-module_location--revamp__text__6Pt-W",
                "[data-testid='property-card-location']",
                "div.styles-module_location__M1i5D"
            ]
            for selector in location_selectors:
                loc_el = card.select_one(selector)
                if loc_el:
                    location = loc_el.get_text(strip=True)
                    break

            # ===== استخراج الدفعة المقدمة =====
            down_payment = "0"
            dp_selectors = [
                "div.tag-module_tag__jFU3w",
                "[data-testid='down-payment']",
                "span.styles-module_tag__G-N0B"
            ]
            for selector in dp_selectors:
                dp_el = card.select_one(selector)
                if dp_el:
                    down_payment = dp_el.get_text(strip=True)
                    break

            # ===== معالجة الموقع =====
            location_parts = location.split(",") if location else None
            city = location_parts[0].strip() if location_parts and len(location_parts) > 0 else None
            state = location_parts[1].strip().split("Compounds")[0].strip() if location_parts and len(location_parts) > 1 else None

            # تجاهل العناصر التي لا تحتوي على رابط (غير عقارات)
            if not link:
                continue

            properties.append({
                "PropertyType": type_ if type_ else None,
                "Link": link,
                "Title": title if title else None,
                "Price": price if price else None,
                "Location": city,
                "State": state,
                "Area": area if area else None,
                "Bedrooms": bedrooms if bedrooms else None,
                "Bathrooms": bathrooms if bathrooms else None,
                "Down_Payment": down_payment,
                "Source": "PropertyFinder",
                "Scrape_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            logger.error(f"خطأ في معالجة كارد PropertyFinder: {e}")
            continue

    return properties


def scrape_all_propertyfinder_pages(base_url, max_pages=10):
    """دالة لجمع البيانات من جميع صفحات PropertyFinder"""
    all_properties = []
    empty_pages = 0  # عداد للصفحات الفارغة

    for page_num in range(1, max_pages + 1):
        if page_num == 1:
            page_url = base_url
        else:
            page_url = f"{base_url}page={page_num}"
        
        logger.info(f"جاري جمع البيانات من PropertyFinder الصفحة {page_num}...")
        properties = scrape_propertyfinder_page(page_url)

        if not properties:
            empty_pages += 1
            logger.warning(f"⚠️ لم يتم العثور على عقارات في الصفحة {page_num}")
            # توقف بعد 3 صفحات فارغة متتالية
            if empty_pages >= 3:
                logger.info(f"🛑 توقف بعد {empty_pages} صفحات فارغة متتالية")
                break
        else:
            empty_pages = 0  # إعادة تعيين العداد عند العثور على عقارات
            all_properties.extend(properties)
            logger.info(f"✅ تم جمع {len(properties)} عقار من PropertyFinder الصفحة {page_num}")

        time.sleep(2)  # زيادة وقت الانتظار لتجنب الحظر

    logger.info(f"📊 إجمالي العقارات المجمعة: {len(all_properties)}")
    return all_properties

# ============= دوال تشغيل dbt =============

def run_dbt_command(command: str, project_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    تشغيل أمر dbt
    
    Args:
        command: أمر dbt لتشغيله (مثل 'run', 'test', 'build')
        project_dir: مسار مشروع dbt (اختياري)
    
    Returns:
        dict: يحتوي على نتيجة التنفيذ
    """
    try:
        # بناء الأمر
        cmd_parts = ["dbt", command]
        
        # إضافة مسار المشروع إذا تم تحديده
        if project_dir:
            cmd_parts.extend(["--project-dir", project_dir])
        
        # إضافة --profiles-dir إذا كان موجوداً
        profiles_dir = os.environ.get("DBT_PROFILES_DIR")
        if profiles_dir:
            cmd_parts.extend(["--profiles-dir", profiles_dir])
        
        cmd = " ".join(cmd_parts)
        logger.info(f"🔧 تشغيل أمر dbt: {cmd}")
        
        # تشغيل الأمر
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 دقائق كحد أقصى
        )
        
        return {
            "success": result.returncode == 0,
            "command": cmd,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timestamp": datetime.now().isoformat()
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "command": cmd,
            "error": "Timeout - تم تجاوز الحد الأقصى للوقت (10 دقائق)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "command": command,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ============= إعداد FastAPI =============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    logger.info("🚀 بدء تشغيل Real Estate Scraper API (بيانات خام)")
    logger.info("📍 السيرفر يعمل على: http://localhost:8000")
    
    if not os.path.exists("scraped_data_raw.csv"):
        empty_df = pd.DataFrame(columns=[
            "PropertyType", "Link", "Title", "Price", "Location", 
            "Area", "Bedrooms", "Bathrooms", "Down_Payment", 
            "Source", "Scrape_Date"
        ])
        empty_df.to_csv("scraped_data_raw.csv", index=False)
        logger.info("✅ تم إنشاء ملف CSV جديد")
    
    if not os.path.exists("scraped_data_raw.json"):
        with open("scraped_data_raw.json", 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        logger.info("✅ تم إنشاء ملف JSON جديد")
    
    yield
    logger.info("⏹️ إيقاف تشغيل Real Estate Scraper API")

app = FastAPI(
    title="Real Estate Scraper API",
    description="API لجمع بيانات العقارات من PropertyFinder و Bayut مع دعم تشغيل dbt",
    version="1.0.0",
    lifespan=lifespan
)

# إضافة CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= نماذج البيانات =============

class ScrapeRequest(BaseModel):
    """نموذج طلب السكراب"""
    propertyfinder_pages: Optional[int] = 5

class DbtRunRequest(BaseModel):
    """نموذج طلب تشغيل dbt"""
    command: Optional[str] = "run"  # run, test, build, compile, etc.
    project_dir: Optional[str] = None  # مسار مشروع dbt

# ============= تخزين المهام =============

scraping_tasks: Dict[str, Dict[str, Any]] = {}
DATA_FILE = "scraped_data_raw.csv"
JSON_FILE = "scraped_data_raw.json"

# ============= دوال الحفظ =============

def save_raw_data(df, save_csv=True, save_json=True):
    """حفظ البيانات الخام بدون أي تنظيف"""
    if df.empty:
        logger.warning("⚠️ لا توجد بيانات للحفظ")
        return
    
    try:
        if save_csv:
            expected_columns = [
                "PropertyType", "Link", "Title", "Price", "Location", 
                "Area", "Bedrooms", "Bathrooms", "Down_Payment", 
                "Source", "Scrape_Date"
            ]
            
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = None
            
            if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
                try:
                    df_existing = pd.read_csv(DATA_FILE)
                    if not df_existing.empty:
                        df_combined = pd.concat([df_existing, df], ignore_index=True)
                        if "Link" in df_combined.columns:
                            df_combined = df_combined.drop_duplicates(subset=["Link"], keep="last")
                        df_combined.to_csv(DATA_FILE, index=False)
                        logger.info(f"✅ تم حفظ {len(df_combined)} عقار في {DATA_FILE}")
                    else:
                        df.to_csv(DATA_FILE, index=False)
                        logger.info(f"✅ تم حفظ {len(df)} عقار في {DATA_FILE}")
                except Exception as e:
                    logger.error(f"خطأ في قراءة الملف: {e}")
                    df.to_csv(DATA_FILE, index=False)
                    logger.info(f"✅ تم حفظ {len(df)} عقار في {DATA_FILE} (تم إنشاء ملف جديد)")
            else:
                df.to_csv(DATA_FILE, index=False)
                logger.info(f"✅ تم حفظ {len(df)} عقار في {DATA_FILE} (ملف جديد)")

        if save_json:
            df_clean = df.replace({np.nan: None, np.inf: None, -np.inf: None})
            records = dataframe_to_json_safe(df_clean)
            
            if os.path.exists(JSON_FILE) and os.path.getsize(JSON_FILE) > 0:
                try:
                    with open(JSON_FILE, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    if existing_data:
                        existing_df = pd.DataFrame(existing_data)
                        combined_df = pd.concat([existing_df, df_clean], ignore_index=True)
                        if "Link" in combined_df.columns:
                            combined_df = combined_df.drop_duplicates(subset=["Link"], keep="last")
                        combined_records = dataframe_to_json_safe(combined_df)
                        with open(JSON_FILE, 'w', encoding='utf-8') as f:
                            json.dump(combined_records, f, ensure_ascii=False, indent=4)
                        logger.info(f"✅ تم حفظ {len(combined_records)} عقار في {JSON_FILE}")
                    else:
                        with open(JSON_FILE, 'w', encoding='utf-8') as f:
                            json.dump(records, f, ensure_ascii=False, indent=4)
                        logger.info(f"✅ تم حفظ {len(records)} عقار في {JSON_FILE}")
                except Exception as e:
                    logger.error(f"خطأ في قراءة ملف JSON: {e}")
                    with open(JSON_FILE, 'w', encoding='utf-8') as f:
                        json.dump(records, f, ensure_ascii=False, indent=4)
                    logger.info(f"✅ تم حفظ {len(records)} عقار في {JSON_FILE} (تم إنشاء ملف جديد)")
            else:
                with open(JSON_FILE, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=4)
                logger.info(f"✅ تم حفظ {len(records)} عقار في {JSON_FILE} (ملف جديد)")
                
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ البيانات: {e}")

# ============= تنفيذ مهمة السكراب =============

async def run_scraping_task(task_id: str, params: dict):
    """تنفيذ مهمة السكراب في الخلفية"""
    try:
        scraping_tasks[task_id]["status"] = "running"
        scraping_tasks[task_id]["message"] = "جاري جمع البيانات..."

        propertyfinder_url = "https://www.propertyfinder.eg/en/search?l=30754&c=1&fu=0&ob=mr&"

        propertyfinder_pages = params.get("propertyfinder_pages", 1)

        total_pages = propertyfinder_pages
        completed_pages = 0
        all_properties = []

        if propertyfinder_pages > 0:
            scraping_tasks[task_id]["message"] = "جاري جمع البيانات من PropertyFinder..."
            propertyfinder_properties = scrape_all_propertyfinder_pages(
                propertyfinder_url,
                max_pages=propertyfinder_pages
            )
            all_properties.extend(propertyfinder_properties)
            completed_pages += propertyfinder_pages
            scraping_tasks[task_id]["progress"] = int((completed_pages / total_pages) * 100)
            logger.info(f"✅ تم جمع {len(propertyfinder_properties)} عقار من PropertyFinder")


        if not all_properties:
            scraping_tasks[task_id]["status"] = "failed"
            scraping_tasks[task_id]["message"] = "لم يتم جمع أي عقارات"
            scraping_tasks[task_id]["error"] = "No properties found"
            scraping_tasks[task_id]["completed_at"] = datetime.now().isoformat()
            return

        df = pd.DataFrame(all_properties)
        df.drop_duplicates(subset=["Link"], inplace=True)
        df.dropna(subset=["Link"], inplace=True)
        df['Bathrooms'] = df['Bathrooms'].str.replace("+", "", case=False, regex=False)
        df['Bedrooms'] = df['Bedrooms'].str.replace("+", "", case=False, regex=False)
        df['Bathrooms'] = df['Bathrooms'].str.replace("Studio", "1", case=False, regex=False)
        df['Bedrooms'] = df['Bedrooms'].str.replace("Studio", "1", case=False, regex=False)
        df = df.astype({'Bedrooms': 'int'})
        df = df.astype({'Bathrooms': 'int'})

        expected_columns = [
            "PropertyType", "Link", "Title", "Price", "Location", 
            "Area", "Bedrooms", "Bathrooms", "Down_Payment", 
            "Source", "Scrape_Date"
        ]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None

        save_raw_data(df, save_csv=True, save_json=True)

        result_data = dataframe_to_json_safe(df)

        scraping_tasks[task_id]["status"] = "completed"
        scraping_tasks[task_id]["progress"] = 100
        scraping_tasks[task_id]["message"] = f"✅ تم جمع {len(df)} عقار بنجاح"
        scraping_tasks[task_id]["total"] = len(df)
        scraping_tasks[task_id]["completed_at"] = datetime.now().isoformat()
        scraping_tasks[task_id]["result"] = result_data

        logger.info(f"✅ المهمة {task_id} اكتملت بنجاح مع {len(df)} عقار")

    except Exception as e:
        logger.error(f"❌ المهمة {task_id} فشلت: {e}")
        import traceback
        traceback.print_exc()
        scraping_tasks[task_id]["status"] = "failed"
        scraping_tasks[task_id]["error"] = str(e)
        scraping_tasks[task_id]["message"] = f"فشل في جمع البيانات: {str(e)}"
        scraping_tasks[task_id]["completed_at"] = datetime.now().isoformat()

# ============= نقاط النهاية =============

@app.get("/")
async def root():
    """الصفحة الرئيسية"""
    return {
        "message": "Real Estate Scraper API (Raw Data - No Cleaning)",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "/": "GET - هذه الصفحة",
            "/scrape": "POST أو GET - بدء عملية جمع البيانات",
            "/scrape/status/{task_id}": "GET - إرجاع البيانات فقط (JSON للعقارات)",
            "/scrape/tasks": "GET - عرض جميع المهام",
            "/data": "GET - عرض البيانات المخزنة كـ JSON",
            "/data/export/csv": "GET - تحميل البيانات كـ CSV",
            "/data/export/json": "GET - تحميل البيانات كـ JSON",
            "/data/stats": "GET - إحصائيات عن البيانات",
            "/api/dbt/run": "POST - تشغيل أوامر dbt (run, test, build, compile)"
        }
    }


@app.api_route("/scrape", methods=["GET", "POST"])
async def start_scraping(
    request: ScrapeRequest = None,
    background_tasks: BackgroundTasks = None,
    propertyfinder_pages: Optional[int] = Query(5, description="عدد صفحات PropertyFinder"),
    bayut_pages: Optional[int] = Query(1, description="عدد صفحات Bayut")
):
    """
    بدء عملية جمع البيانات من المواقع (يدعم GET و POST)
    
    للاستخدام مع GET:
    /scrape?propertyfinder_pages=2&bayut_pages=1
    """
    if request and hasattr(request, 'dict'):
        params = request.dict()
    else:
        params = {
            "propertyfinder_pages": propertyfinder_pages,
            "bayut_pages": bayut_pages
        }
    
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    scraping_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "total": 0,
        "message": "⏳ تم إنشاء المهمة",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None
    }
    
    background_tasks.add_task(run_scraping_task, task_id, params)
    
    return {
        "success": True,
        "task_id": task_id,
        "status": "pending",
        "message": "⏳ تم بدء عملية جمع البيانات",
        "params": params,
        "check_status_url": f"/scrape/status/{task_id}",
        "data_url": "/data"
    }


@app.get("/scrape/status/{task_id}")
async def get_scrape_status(task_id: str):
    """
    إرجاع بيانات العقارات فقط كـ JSON (بدون أي حقول إضافية)
    """
    if task_id not in scraping_tasks:
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found", "message": f"المهمة {task_id} غير موجودة"}
        )
    
    task_data = scraping_tasks[task_id]
    
    # إذا كانت المهمة مكتملة ولديها نتائج
    if task_data["status"] == "completed" and task_data.get("result"):
        # إرجاع البيانات فقط (قائمة العقارات)
        result = task_data["result"]
        if isinstance(result, list):
            result = convert_nan_to_none(result)
        elif isinstance(result, dict):
            result = convert_nan_to_none(result)
        return JSONResponse(content=result)
    
    # إذا كانت المهمة لا تزال قيد التشغيل
    elif task_data["status"] == "running":
        return JSONResponse(
            status_code=202,
            content={
                "status": "running",
                "progress": task_data.get("progress", 0),
                "message": "⏳ جاري جمع البيانات... يرجى الانتظار"
            }
        )
    
    # إذا كانت المهمة فشلت
    elif task_data["status"] == "failed":
        return JSONResponse(
            status_code=500,
            content={
                "error": task_data.get("error", "Unknown error"),
                "message": "❌ فشل في جمع البيانات"
            }
        )
    
    # إذا كانت المهمة لا تزال معلقة
    else:
        return JSONResponse(
            status_code=202,
            content={
                "status": "pending",
                "message": "⏳ المهمة في قائمة الانتظار"
            }
        )


@app.get("/scrape/status/{task_id}/full")
async def get_scrape_status_full(task_id: str):
    """
    إرجاع الحالة الكاملة للمهمة (مع البيانات والتفاصيل)
    """
    if task_id not in scraping_tasks:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    
    task_data = scraping_tasks[task_id]
    
    result = task_data.get("result")
    if result is not None:
        if isinstance(result, list):
            result = convert_nan_to_none(result)
        elif isinstance(result, dict):
            result = convert_nan_to_none(result)
    
    return {
        "task_id": task_id,
        "status": task_data["status"],
        "progress": task_data.get("progress", 0),
        "total": task_data.get("total", 0),
        "message": task_data.get("message"),
        "result": result,
        "error": task_data.get("error"),
        "created_at": task_data["created_at"],
        "completed_at": task_data.get("completed_at")
    }


@app.get("/scrape/tasks")
async def get_all_tasks():
    """الحصول على قائمة بجميع المهام"""
    return {
        "success": True,
        "tasks": [
            {
                "task_id": task_id,
                "status": data["status"],
                "created_at": data["created_at"],
                "completed_at": data.get("completed_at"),
                "message": data.get("message"),
                "total": data.get("total", 0)
            }
            for task_id, data in scraping_tasks.items()
        ]
    }


@app.get("/data")
async def get_data(
    limit: Optional[int] = Query(None, description="عدد النتائج"),
    offset: Optional[int] = Query(0, description="الإزاحة"),
    source: Optional[str] = Query(None, description="تصفية حسب المصدر (PropertyFinder/Bayut)")
):
    """الحصول على البيانات المخزنة كـ JSON"""
    try:
        if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
            return {
                "success": True,
                "total": 0,
                "data": [],
                "message": "لا توجد بيانات مخزنة"
            }
        
        df = pd.read_csv(DATA_FILE)
        
        if df.empty:
            return {
                "success": True,
                "total": 0,
                "data": [],
                "message": "الملف فارغ"
            }
        
        if source:
            df = df[df["Source"] == source]
        
        total = len(df)
        
        if limit is not None and limit > 0:
            df = df.iloc[offset:offset + limit]
        
        data = dataframe_to_json_safe(df)
        
        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"خطأ في جلب البيانات: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "حدث خطأ أثناء جلب البيانات"
        }


@app.get("/data/export/csv")
async def export_csv():
    """تصدير البيانات كملف CSV"""
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        raise HTTPException(status_code=404, detail="لا توجد بيانات للتصدير")
    
    return FileResponse(
        DATA_FILE,
        media_type="text/csv",
        filename=f"properties_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )


@app.get("/data/export/json")
async def export_json():
    """تصدير البيانات كملف JSON آمن"""
    if not os.path.exists(JSON_FILE) or os.path.getsize(JSON_FILE) == 0:
        raise HTTPException(status_code=404, detail="لا توجد بيانات للتصدير")
    
    return FileResponse(
        JSON_FILE,
        media_type="application/json",
        filename=f"properties_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )


@app.get("/data/stats")
async def get_stats():
    """الحصول على إحصائيات عن البيانات الخام"""
    try:
        if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
            return {
                "success": True,
                "total_properties": 0,
                "message": "لا توجد بيانات"
            }
        
        df = pd.read_csv(DATA_FILE)
        
        if df.empty:
            return {
                "success": True,
                "total_properties": 0,
                "message": "الملف فارغ"
            }
        
        stats = {
            "success": True,
            "total_properties": len(df),
            "updated_at": datetime.now().isoformat()
        }
        
        if "Source" in df.columns:
            stats["sources"] = df["Source"].value_counts().to_dict()
        
        if "PropertyType" in df.columns:
            stats["property_types"] = df["PropertyType"].value_counts().head(10).to_dict()
        
        if "Scrape_Date" in df.columns:
            stats["last_scrape_date"] = df["Scrape_Date"].iloc[-1] if not df.empty else None
        
        if "Location" in df.columns:
            stats["top_locations"] = df["Location"].value_counts().head(5).to_dict()
        
        return stats
        
    except Exception as e:
        logger.error(f"خطأ في جلب الإحصائيات: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "حدث خطأ أثناء جلب الإحصائيات"
        }


@app.delete("/data")
async def clear_data():
    """حذف جميع البيانات المخزنة"""
    try:
        empty_df = pd.DataFrame(columns=[
            "PropertyType", "Link", "Title", "Price", "Location", 
            "Area", "Bedrooms", "Bathrooms", "Down_Payment", 
            "Source", "Scrape_Date"
        ])
        
        empty_df.to_csv(DATA_FILE, index=False)
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        
        return {
            "success": True,
            "message": "✅ تم حذف جميع البيانات بنجاح",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"خطأ في حذف البيانات: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "حدث خطأ أثناء حذف البيانات"
        }


# ============= نقطة نهاية dbt =============

@app.post("/api/dbt/run")
async def dbt_run(
    request: DbtRunRequest,
    background_tasks: BackgroundTasks
):
    """
    تشغيل أمر dbt (run, test, build, compile, etc.)
    
    مثال:
    {
        "command": "run",
        "project_dir": "/path/to/dbt/project"
    }
    
    أوامر dbt المدعومة:
    - run: تشغيل نماذج dbt
    - test: تشغيل اختبارات dbt
    - build: بناء نماذج واختبارات dbt
    - compile: ترجمة نماذج dbt
    - seed: تحميل البيانات من ملفات CSV
    - snapshot: تشغيل لقطات dbt
    - docs generate: إنشاء وثائق dbt
    """
    try:
        # التحقق من أن dbt مثبت
        try:
            subprocess.run(["dbt", "--version"], capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "dbt غير مثبت أو غير متوفر في النظام",
                    "message": "يرجى تثبيت dbt أولاً: pip install dbt-core dbt-postgres"
                }
            )
        except FileNotFoundError:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "dbt غير مثبت أو غير متوفر في النظام",
                    "message": "يرجى تثبيت dbt أولاً: pip install dbt-core dbt-postgres"
                }
            )
        
        # التحقق من الأمر المدعوم
        supported_commands = ["run", "test", "build", "compile", "seed", "snapshot", "docs"]
        command_parts = request.command.split()
        
        if command_parts[0] not in supported_commands:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"أمر غير مدعوم: {command_parts[0]}",
                    "supported_commands": supported_commands
                }
            )
        
        # التحقق من وجود المشروع
        project_dir = request.project_dir or os.getcwd()
        if not os.path.exists(project_dir):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"مسار المشروع غير موجود: {project_dir}"
                }
            )
        
        # التحقق من وجود ملف dbt_project.yml
        dbt_project_file = os.path.join(project_dir, "dbt_project.yml")
        if not os.path.exists(dbt_project_file):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"ملف dbt_project.yml غير موجود في: {project_dir}",
                    "message": "تأكد من أن المسار يحتوي على مشروع dbt صحيح"
                }
            )
        
        # تشغيل الأمر
        logger.info(f"🔧 تشغيل أمر dbt: {request.command} في {project_dir}")
        
        result = run_dbt_command(request.command, project_dir)
        
        # إضافة معلومات إضافية
        result["project_dir"] = project_dir
        result["command_requested"] = request.command
        
        if result["success"]:
            logger.info(f"✅ نجح تشغيل dbt: {request.command}")
        else:
            logger.error(f"❌ فشل تشغيل dbt: {request.command}")
            
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل dbt: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "حدث خطأ أثناء تشغيل أمر dbt"
            }
        )


@app.get("/api/dbt/check")
async def dbt_check():
    """
    التحقق من تثبيت dbt وعرض معلومات الإصدار
    """
    try:
        # التحقق من وجود dbt
        result = subprocess.run(
            ["dbt", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # استخراج معلومات الإصدار
            version_info = {}
            lines = result.stdout.split('\n')
            for line in lines:
                if 'installed' in line.lower():
                    parts = line.split(':')
                    if len(parts) >= 2:
                        version_info['dbt_version'] = parts[1].strip()
                elif 'postgres' in line.lower() or 'core' in line.lower():
                    if 'version' in line.lower():
                        version_info['plugin_version'] = line.strip()
            
            return {
                "success": True,
                "dbt_installed": True,
                "version_info": version_info,
                "raw_output": result.stdout,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "dbt_installed": False,
                "error": result.stderr,
                "message": "dbt مثبت لكن حدث خطأ في التحقق"
            }
            
    except FileNotFoundError:
        return {
            "success": False,
            "dbt_installed": False,
            "error": "dbt غير مثبت",
            "message": "يرجى تثبيت dbt: pip install dbt-core dbt-postgres"
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "dbt_installed": True,
            "error": "Timeout",
            "message": "انتهى وقت التحقق من dbt"
        }
    except Exception as e:
        return {
            "success": False,
            "dbt_installed": False,
            "error": str(e),
            "message": "حدث خطأ أثناء التحقق من dbt"
        }


@app.get("/api/dbt/list-projects")
async def list_dbt_projects():
    """
    قائمة بمشاريع dbt المتاحة (في المستوى الحالي)
    """
    try:
        current_dir = os.getcwd()
        projects = []
        
        # البحث عن مشاريع dbt في الدليل الحالي
        for item in os.listdir(current_dir):
            item_path = os.path.join(current_dir, item)
            if os.path.isdir(item_path):
                dbt_project_file = os.path.join(item_path, "dbt_project.yml")
                if os.path.exists(dbt_project_file):
                    projects.append({
                        "name": item,
                        "path": item_path,
                        "has_dbt_project": True
                    })
        
        # البحث عن مشاريع في الدليل الحالي نفسه
        if os.path.exists(os.path.join(current_dir, "dbt_project.yml")):
            projects.append({
                "name": ".",
                "path": current_dir,
                "has_dbt_project": True
            })
        
        return {
            "success": True,
            "current_directory": current_dir,
            "projects_found": len(projects),
            "projects": projects,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "حدث خطأ أثناء البحث عن مشاريع dbt"
        }

# ============= تشغيل التطبيق =============

if __name__ == "__main__":
    uvicorn.run(
        "api_scraper_final:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )