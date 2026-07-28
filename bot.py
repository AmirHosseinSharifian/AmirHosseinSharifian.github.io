import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --------------------------------------------
# MEDICAL REFERENCE RANGES
# --------------------------------------------
REFERENCE_RANGES = {
    "hemoglobin": {
        "synonyms": [r"hb", r"hgb", r"haemoglobin"],
        "unit": "g/dL", "min": 12.0, "max": 16.0,
        "category": "🧬 Complete Blood Count",
        "desc": "Oxygen-carrying protein.",
        "clinical_low": "🩺 *Low*: May indicate anemia, iron deficiency, or chronic disease. 📌 *Action*: Eat iron-rich foods (red meat, spinach) and consider a Ferritin test.",
        "clinical_high": "🩺 *High*: May indicate dehydration, smoking, or polycythemia. 📌 *Action*: Increase water intake and consult a physician."
    },
    "wbc": {
        "synonyms": [r"white blood cell", r"leukocytes"],
        "unit": "x10^3/µL", "min": 4.5, "max": 11.0,
        "category": "🧬 Complete Blood Count",
        "desc": "Fights infections.",
        "clinical_low": "🩺 *Low*: May indicate bone marrow issues, viral infections, or autoimmune conditions.",
        "clinical_high": "🩺 *High*: Often indicates infection, inflammation, or stress. Monitor for fever."
    },
    "platelets": {
        "synonyms": [r"plt", r"thrombocytes"],
        "unit": "x10^3/µL", "min": 150, "max": 400,
        "category": "🧬 Complete Blood Count",
        "desc": "Helps blood clotting.",
        "clinical_low": "🩺 *Low*: Risk of bruising/bleeding. May be due to infections or medications.",
        "clinical_high": "🩺 *High*: May indicate inflammation, iron deficiency, or post-surgery recovery."
    },
    "glucose": {
        "synonyms": [r"sugar", r"fasting blood sugar", r"fbs"],
        "unit": "mg/dL", "min": 70, "max": 100,
        "category": "🧪 Metabolic",
        "desc": "Blood sugar (fasting).",
        "clinical_low": "🩺 *Low*: Hypoglycemia. Eat a small snack with complex carbs. If recurrent, check insulin levels.",
        "clinical_high": "🩺 *High*: Prediabetes/Diabetes risk. 📌 *Action*: Reduce sugary drinks, exercise daily, and monitor Hba1c."
    },
    "creatinine": {
        "synonyms": [r"creat"],
        "unit": "mg/dL", "min": 0.7, "max": 1.3,
        "category": "🧪 Metabolic",
        "desc": "Kidney function marker.",
        "clinical_low": "🩺 *Low*: Usually not concerning; may indicate low muscle mass.",
        "clinical_high": "🩺 *High*: Possible kidney impairment. 📌 *Action*: Stay hydrated and avoid excess NSAIDs. Check eGFR."
    },
    "sodium": {
        "synonyms": [r"na"],
        "unit": "mEq/L", "min": 136, "max": 145,
        "category": "🧪 Metabolic",
        "desc": "Electrolyte balance.",
        "clinical_low": "🩺 *Low*: Hyponatremia. May be due to kidney issues or excessive water intake.",
        "clinical_high": "🩺 *High*: Hypernatremia. Usually due to dehydration. Increase water intake."
    },
    "potassium": {
        "synonyms": [r"k"],
        "unit": "mEq/L", "min": 3.5, "max": 5.0,
        "category": "🧪 Metabolic",
        "desc": "Electrolyte balance.",
        "clinical_low": "🩺 *Low*: Hypokalemia. Eat bananas, avocados, and potatoes.",
        "clinical_high": "🩺 *High*: Hyperkalemia. Reduce high-potassium foods and consult a doctor immediately."
    },
    "cholesterol": {
        "synonyms": [r"total cholesterol", r"chol"],
        "unit": "mg/dL", "min": 125, "max": 200,
        "category": "🫀 Lipid Panel",
        "desc": "Total cholesterol.",
        "clinical_low": "🩺 *Low*: Usually not concerning unless extremely low.",
        "clinical_high": "🩺 *High*: Hyperlipidemia. 📌 *Action*: Reduce saturated fats, increase fiber (oats, beans)."
    },
    "ldl": {
        "synonyms": [r"bad cholesterol", r"low-density lipoprotein"],
        "unit": "mg/dL", "min": 0, "max": 100,
        "category": "🫀 Lipid Panel",
        "desc": "LDL ('Bad' cholesterol).",
        "clinical_low": "🩺 Low is ideal for LDL.",
        "clinical_high": "🩺 *High*: Major risk for heart disease. 📌 *Action*: Reduce trans fats, increase exercise, and consider a statin if very high."
    },
    "hdl": {
        "synonyms": [r"good cholesterol", r"high-density lipoprotein"],
        "unit": "mg/dL", "min": 40, "max": 100,
        "category": "🫀 Lipid Panel",
        "desc": "HDL ('Good' cholesterol).",
        "clinical_low": "🩺 *Low*: Increased heart risk. 📌 *Action*: Regular exercise, omega-3 fatty acids (fish oil).",
        "clinical_high": "🩺 *High*: Excellent! Generally protective against heart disease."
    },
    "triglycerides": {
        "synonyms": [r"trig", r"tg"],
        "unit": "mg/dL", "min": 0, "max": 150,
        "category": "🫀 Lipid Panel",
        "desc": "Fat storage in blood.",
        "clinical_low": "🩺 Low is generally good.",
        "clinical_high": "🩺 *High*: Risk of pancreatitis and heart disease. 📌 *Action*: Reduce sugar, alcohol, and refined carbs."
    },
    "iron": {
        "synonyms": [r"fe", r"serum iron"],
        "unit": "µg/dL", "min": 60, "max": 170,
        "category": "🧪 Vitamins & Minerals",
        "desc": "Essential mineral.",
        "clinical_low": "🩺 *Low*: Iron deficiency anemia. 📌 *Action*: Vitamin C with meals enhances absorption. Eat red meat.",
        "clinical_high": "🩺 *High*: May indicate iron overload (hemochromatosis). Consider a Ferritin test."
    },
    "b12": {
        "synonyms": [r"vitamin b12", r"cobalamin"],
        "unit": "pg/mL", "min": 200, "max": 900,
        "category": "🧪 Vitamins & Minerals",
        "desc": "Nerve & energy.",
        "clinical_low": "🩺 *Low*: Fatigue, neuropathy. 📌 *Action*: Increase animal products or supplement B12. Check for absorption issues.",
        "clinical_high": "🩺 *High*: Usually harmless as excess is excreted, but reduce supplements if extreme."
    },
    "vitamin_d": {
        "synonyms": [r"vit d", r"calciferol"],
        "unit": "ng/mL", "min": 30, "max": 100,
        "category": "🧪 Vitamins & Minerals",
        "desc": "Bone health & immunity.",
        "clinical_low": "🩺 *Low*: Common. 📌 *Action*: Sunlight exposure 15 mins/day, supplement D3, and take with fatty meals.",
        "clinical_high": "🩺 *High*: Toxicity is rare. Reduce supplements if taking large doses."
    },
    "tsh": {
        "synonyms": [r"thyroid stimulating hormone"],
        "unit": "mIU/L", "min": 0.4, "max": 4.0,
        "category": "🧪 Hormones",
        "desc": "Thyroid function.",
        "clinical_low": "🩺 *Low*: Hyperthyroidism (overactive). May cause weight loss, anxiety.",
        "clinical_high": "🩺 *High*: Hypothyroidism (underactive). May cause fatigue, weight gain. Consult an endocrinologist."
    }
}

# --------------------------------------------
# ANALYZER FUNCTION
# --------------------------------------------
def analyze_blood_test(text):
    text = text.lower()
    found_results = []
    summary = {"normal": 0, "borderline": 0, "abnormal": 0}
    categories_used = set()

    for param, info in REFERENCE_RANGES.items():
        synonyms_list = [param] + info["synonyms"]
        synonyms_list.sort(key=len, reverse=True)
        pattern_parts = [re.escape(syn) for syn in synonyms_list]
        pattern = rf'({"|".join(pattern_parts)})\s*:?\s*(\d+\.?\d*)'
        match = re.search(pattern, text)

        if match:
            value = float(match.group(2))
            min_val = info["min"]
            max_val = info["max"]
            range_width = max_val - min_val
            border_low = min_val + (range_width * 0.1) if range_width > 0 else min_val
            border_high = max_val - (range_width * 0.1) if range_width > 0 else max_val

            categories_used.add(info["category"])

            if value < min_val:
                status = "🔽 Abnormal Low"
                status_icon = "🔽"
                advice = info.get("clinical_low", f"Below range ({min_val}-{max_val}).")
                summary["abnormal"] += 1
            elif value < border_low:
                status = "⚠️ Borderline Low"
                status_icon = "⚠️"
                advice = f"Slightly below optimal ({min_val}-{max_val}). Monitor closely."
                summary["borderline"] += 1
            elif value > max_val:
                status = "🔼 Abnormal High"
                status_icon = "🔼"
                advice = info.get("clinical_high", f"Above range ({min_val}-{max_val}).")
                summary["abnormal"] += 1
            elif value > border_high:
                status = "⚠️ Borderline High"
                status_icon = "⚠️"
                advice = f"Slightly above optimal ({min_val}-{max_val}). Monitor closely."
                summary["borderline"] += 1
            else:
                status = "✅ Normal"
                status_icon = "✅"
                advice = f"Optimal range ({min_val}-{max_val} {info['unit']}). Keep it up!"
                summary["normal"] += 1

            found_results.append({
                "category": info["category"],
                "param": param.capitalize(),
                "value": f"{value} {info['unit']}",
                "status": status,
                "status_icon": status_icon,
                "advice": advice
            })

    if not found_results:
        return ("❌ I couldn't recognize any parameters. Send like: `Hb 14.5, WBC 7.2, Glucose 90, LDL 95, TSH 2.5`")

    # Build response
    total = summary["normal"] + summary["borderline"] + summary["abnormal"]
    summary_line = f"🧑‍⚕️ *Health Summary*: {summary['normal']} Normal, {summary['borderline']} Borderline, {summary['abnormal']} Abnormal (out of {total})."

    if summary["abnormal"] >= 2:
        summary_line += "\n⚠️ *Action Required*: Several values are out of range. Please show this to your doctor."
    elif summary["abnormal"] == 1:
        summary_line += "\n📝 *Suggestion*: One abnormal value found. Monitor closely or consult a professional."
    else:
        summary_line += "\n✅ *Great job!* Your values are generally healthy."

    found_results.sort(key=lambda x: x["category"])
    detailed_text = ""
    current_category = None
    for res in found_results:
        if res["category"] != current_category:
            detailed_text += f"\n\n📂 *{res['category']}*\n"
            current_category = res["category"]
        detailed_text += (f"  • *{res['param']}*: {res['value']} → {res['status']}\n"
                          f"    {res['advice']}\n")

    full_reply = f"{summary_line}\n\n---\n📊 *Detailed Analysis:*{detailed_text}\n\n---\n⚠️ *Medical Disclaimer*: This AI assistant provides educational insights only. It does NOT replace a certified medical professional. Please consult your doctor for diagnosis and treatment."
    return full_reply

# --------------------------------------------
# BOT HANDLERS
# --------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🩸 *Welcome to the Advanced Blood Test Analyzer!*\n\n"
        "Send me your results in a single text:\n"
        "`Hb 15, WBC 8.2, Glucose 95, LDL 80, TSH 2.1`\n\n"
        "✅ Supports abbreviations (Hb, Plt, Na, K, TSH)\n"
        "✅ Groups by medical panels\n"
        "✅ Provides lifestyle & clinical advice",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    reply = analyze_blood_test(user_text)
    await update.message.reply_text(reply, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Try sending: `Hemoglobin 12.5, Glucose 110, LDL 130, Triglycerides 160, TSH 3.8`\n"
        "I'll flag the high glucose, LDL, and Triglycerides with specific health tips!",
        parse_mode="Markdown"
    )

# --------------------------------------------
# MAIN - READ TOKEN FROM ENVIRONMENT
# --------------------------------------------
def main():
    TOKEN = os.environ.get('BOT_TOKEN')
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable not set!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running with ENHANCED features! Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()