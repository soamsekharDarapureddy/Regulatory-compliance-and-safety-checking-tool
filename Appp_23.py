# app.py
import streamlit as st
import pandas as pd
import pdfplumber
import openpyxl
import re
import os
import base64

# To parse .docx files, you need to install python-docx
try:
    import docx
except ImportError:
    st.error("The 'python-docx' library is not installed. Please install it by running: pip install python-docx")
    st.stop()

# === Branding & Page Config ===
st.set_page_config(page_title="Regulatory Compliance & Safety Tool", layout="wide")

# === Advanced CSS for Styling ===
st.markdown("""
<style>
:root { --accent:#0056b3; --panel:#f3f8fc; --shadow:#cfe7ff; }
.card{background:#fff; border-radius:10px; padding:12px 14px; margin-bottom:10px; border-left:8px solid #c9d6e8;}
.small-muted{color:#777; font-size:0.95em;}
.result-pass{color:#1e9f50; font-weight:700;}
.result-fail{color:#c43a31; font-weight:700;}
.result-na{color:#808080; font-weight:700;}
a {text-decoration: none;}
.main .block-container { padding-top: 2rem; }
.component-label { font-weight: bold; color: #333; }
.component-value { color: #555; }
</style>
""", unsafe_allow_html=True)

# === Session State Initialization ===
def init_session_state():
    state_defaults = {
        "reports_verified": 0, "requirements_generated": 0, "found_component": None, 
        "component_db": pd.DataFrame()
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()

# === FINAL HEADER with visual adjustments ===
def get_image_as_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

logo_base64 = get_image_as_base64("people_tech_logo.png")

if logo_base64:
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 25px;">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 100px; margin-right: 25px;"/>
            <div>
                <h1 style="color:#0056b3; margin: 0; font-size: 2.5em; line-height: 1.1;">Regulatory Compliance</h1>
                <h2 style="color:#0056b3; margin: 0; font-size: 1.6em; line-height: 1.1;">& Safety Verification Tool</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.title("Regulatory Compliance & Safety Verification Tool")


# === KNOWLEDGE BASES ===
KEYWORD_TO_STANDARD_MAP = {
    "gps": "NMEA 0183", "gnss": "3GPP", "bluetooth": "Bluetooth Core Specification", "wifi": "IEEE 802.11",
    "lte": "3GPP LTE", "can": "ISO 11898", "sensor": "AEC-Q104", "ip rating": "IEC 60529",
    "short circuit": "AIS-156 / IEC 62133", "overcharge": "AIS-156", "vibration": "IEC 60068-2-6"
}
TEST_CASE_KNOWLEDGE_BASE = {
    "over-voltage": {"requirement": "DUT must withstand over-voltage.", "equipment": ["DC Power Supply", "DMM"]},
    "short circuit": {"requirement": "DUT shall safely interrupt short-circuit.", "equipment": ["High-Current Supply", "Oscilloscope"]},
    "vibration": {"requirement": "DUT must withstand vibration without mechanical failure.", "equipment": ["Shaker Table"]},
}

# --- COMPLETE, UNIFIED, and EMBEDDED Component Database ---
UNIFIED_COMPONENT_DB = {
    # VCU, Motor Controller, etc.
    "spc560p50l3": {"Subsystem": "VCU", "Part Name": "32-bit MCU", "Manufacturer": "STMicroelectronics", "Qualification": "AEC-Q100"},
    "tja1051t": {"Subsystem": "VCU", "Part Name": "CAN Transceiver", "Manufacturer": "NXP", "Qualification": "AEC-Q100"},
    "fsbb30ch60f": {"Subsystem": "Motor Controller", "Part Name": "IGBT Module", "Manufacturer": "ON Semi"},
    "bq76952": {"Subsystem": "BMS", "Part Name": "Battery Monitor", "Manufacturer": "Texas Instruments"},

    # Capacitors - Detailed
    "gcm155l81e104ke02d": {"Manufacturer": "Murata", "Product Category": "MLCC - SMD/SMT", "Capacitance": "0.1 uF", "Voltage Rating DC": "25 VDC", "Dielectric": "X8L", "Tolerance": "10 %", "Case Code": "0402", "Min Temp": "-55 C", "Max Temp": "+150 C", "Qualification": "AEC-Q200"},
    "cga3e3x7s1a225k080ae": {"Manufacturer": "TDK", "Product Category": "MLCC - SMD/SMT", "Capacitance": "2.2 uF", "Voltage Rating DC": "10 VDC", "Dielectric": "X7S", "Tolerance": "10 %", "Case Code": "0603", "Qualification": "AEC-Q200"},
    "edk476m050s9haa": {"Manufacturer": "KEMET", "Product Category": "Aluminum Electrolytic", "Capacitance": "47 uF", "Voltage Rating DC": "50 VDC", "Tolerance": "20 %", "Min Temp": "-40 C", "Max Temp": "+105 C"},
    
    # Diodes - Detailed
    "d5v0h1b2lpq-7b": {"Manufacturer": "Diodes Inc.", "Product Category": "ESD Protection Diode", "Peak Pulse Power": "30 W", "Breakdown Voltage": "6V", "Package": "DFN1006", "Qualification": "AEC-Q101"},
    "b340bq-13-f": {"Manufacturer": "Diodes Inc.", "Product Category": "Schottky Diode", "Forward Current": "3A", "Reverse Voltage": "40V", "Package": "SMB", "Qualification": "AEC-Q101"},
    
    # Inductors & Ferrites
    "74279262": {"Manufacturer": "Würth Elektronik", "Product Category": "Ferrite Bead", "Impedance": "220 Ohm @ 100 MHz", "Current Rating": "3A", "Package": "0805"},
    "spm7054vt-220m-d": {"Manufacturer": "TDK", "Product Category": "Power Inductor", "Inductance": "22 uH", "Current Rating": "2.5A", "Package": "SMD", "Qualification": "AEC-Q200"},

    # MOSFETs
    "irfz44n": {"Subsystem": "General", "Part Name": "MOSFET", "Manufacturer": "Infineon", "Voltage": "55V", "Current": "49A"},
    "rq3g270bjfratcb": {"Manufacturer": "Rohm", "Product Category": "MOSFET", "Voltage": "12V", "Current": "27A", "Package": "HSMT8"},

    # Other Components (with placeholders - data to be filled from datasheets)
    "1n4007": {"Subsystem": "General", "Part Name": "Diode", "Manufacturer": "Multiple"},
    "fh28-10s-0.5sh(05)": {"Manufacturer": "Hirose", "part_name": "Connector", "subsystem": "General"},
    "zldo1117qg33ta": {"Manufacturer": "Diodes Incorporated", "part_name": "LDO Regulator", "subsystem": "General"},
    "pca9306idcurq1": {"Manufacturer": "Texas Instruments", "part_name": "Level Translator", "subsystem": "General"},
    "iso1042bqdwvq1": {"Manufacturer": "Texas Instruments", "part_name": "CAN Transceiver", "subsystem": "General"},
    "iam-20680ht": {"Manufacturer": "TDK InvenSense", "part_name": "IMU Sensor", "subsystem": "General"},
    "attiny1616-szt-vao": {"Manufacturer": "Microchip", "part_name": "MCU", "subsystem": "General"},
    "qmc5883l": {"Manufacturer": "QST", "part_name": "Magnetometer", "subsystem": "General"},
    "y4ete00a0aa": {"Manufacturer": "Quectel", "part_name": "LTE Module", "subsystem": "General"},
    "yf0023aa": {"Manufacturer": "Quectel", "part_name": "Wi-Fi/BT Antenna", "subsystem": "General"},
    "mb9df125": {"Subsystem": "Instrument Cluster", "Part Name": "MCU with Graphics", "Manufacturer": "Spansion (Cypress)"},
    "veml6031x00": {"Subsystem": "ALS Board", "Part Name": "Ambient Light Sensor", "Manufacturer": "Vishay"},
}


def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line: continue
        
        test_data = {"TestName": "N/A", "Result": "N/A", "Actual": "N/A", "Standard": "N/A"}
        
        patterns = [
            r'^(.*?)\s*-->\s*(Passed|Failed|Success)\s*-->\s*(.+)$',
            r'^(.*?)\s*-->\s*(.+)$',
            r'^\d+:\s*([A-Z_]+):\s*"([A-Z]+)"$',
            r'^(.+?)\s+is\s+(success|failure|passed|failed)$',
            r'^(.+?)\s+(Failed|Passed)$',
        ]

        match = None
        for p in patterns:
            match = re.match(p, line, re.I)
            if match:
                break
        
        if match:
            groups = match.groups()
            if len(groups) == 3: # Pattern 1
                test_data.update({"TestName": groups[0].strip(), "Result": "PASS" if groups[1].lower() in ["passed", "success"] else "FAIL", "Actual": groups[2].strip()})
            elif len(groups) == 2: # Patterns 2, 3, 4, 5
                result_str = groups[1].lower()
                if "passed" in result_str or "success" in result_str:
                    test_data["Result"] = "PASS"
                elif "failed" in result_str:
                    test_data["Result"] = "FAIL"
                else:
                    test_data["Result"] = "INFO"
                test_data.update({"TestName": groups[0].strip(), "Actual": groups[1].strip()})

            for keyword, standard in KEYWORD_TO_STANDARD_MAP.items():
                if keyword in test_data["TestName"].lower():
                    test_data["Standard"] = standard
                    break
            extracted_tests.append(test_data)
            
    return extracted_tests

def parse_report(uploaded_file):
    if not uploaded_file: return []
    try:
        file_extension = os.path.splitext(uploaded_file.name.lower())[1]
        if file_extension in ['.csv', '.xlsx']:
            df = pd.read_csv(uploaded_file) if file_extension == '.csv' else pd.read_excel(uploaded_file)
            df.columns = [str(c).strip().lower() for c in df.columns]
            rename_map = {'test': 'TestName', 'standard': 'Standard', 'expected': 'Expected', 'actual': 'Actual', 'result': 'Result', 'description': 'Description', 'part': 'TestName', 'manufacturer pn': 'Actual'}
            df.rename(columns=rename_map, inplace=True)
            return df.to_dict('records')
        elif file_extension == '.pdf':
             with pdfplumber.open(uploaded_file) as pdf:
                content = "".join(page.extract_text() + "\n" for page in pdf.pages if page.extract_text())
        else:
            content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        return intelligent_parser(content)
    except Exception as e:
        st.error(f"An error occurred while parsing: {e}")
        return []

def display_test_card(test_case, color):
    details = f"<b>🧪 Test:</b> {test_case.get('TestName', 'N/A')}<br>"
    for key, label in {'Standard': '📘 Standard', 'Expected': '🎯 Expected', 'Actual': '📌 Actual', 'Description': '💬 Description'}.items():
        value = test_case.get(key)
        if pd.notna(value) and str(value).strip() and str(value).lower() not in ['—', 'nan']:
            details += f"<b>{label}:</b> {value}<br>"
    st.markdown(f"<div class='card' style='border-left-color:{color};'>{details}</div>", unsafe_allow_html=True)

# ---- Streamlit App Layout ----
option = st.sidebar.radio("Navigate", ("Test Report Verification", "Test Requirement Generation", "Component Information", "Dashboard & Analytics"))
st.sidebar.info("An integrated tool for automotive compliance.")

# --- Test Report Verification Module ---
if option == "Test Report Verification":
    st.subheader("Upload & Verify Test Report", anchor=False)
    st.caption("Upload reports (PDF, TXT, CSV, XLSX) to extract and display all relevant data.")
    uploaded_file = st.file_uploader("Upload a report file", type=["pdf", "docx", "xlsx", "csv", "txt", "log"])
    if uploaded_file:
        parsed_data = parse_report(uploaded_file)
        if parsed_data:
            st.session_state.reports_verified += 1
            passed = [t for t in parsed_data if "PASS" in str(t.get("Result", "")).upper()]
            failed = [t for t in parsed_data if "FAIL" in str(t.get("Result", "")).upper()]
            others = [t for t in parsed_data if not ("PASS" in str(t.get("Result", "")).upper() or "FAIL" in str(t.get("Result", "")).upper())]
            
            st.markdown(f"### Found {len(passed)} Passed, {len(failed)} Failed, and {len(others)} Other items.")
            
            if passed:
                with st.expander("✅ Passed Cases", expanded=True):
                    for t in passed: display_test_card(t, '#1e9f50')
            if failed:
                with st.expander("🔴 Failed Cases", expanded=True):
                    for t in failed: display_test_card(t, '#c43a31')
            if others:
                with st.expander("ℹ️ Other/Informational Items", expanded=False):
                    for t in others: display_test_card(t, '#808080')
        else:
            st.warning("No recognizable data was extracted.")

# --- Other Modules ---
elif option == "Test Requirement Generation":
    st.subheader("Generate Test Requirements", anchor=False)
    st.caption("Enter test cases to generate formal requirements.")
    text = st.text_area("Test cases (one per line)", "ip rating\nshort circuit test", height=100)
    if st.button("Generate Requirements"):
        cases = [l.strip() for l in text.split("\n") if l.strip()]
        if cases:
            st.session_state.requirements_generated += len(cases)
            st.markdown("#### Generated Requirements")
            for i, case in enumerate(cases):
                req = next((info for key, info in TEST_CASE_KNOWLEDGE_BASE.items() if key in case.lower()), None)
                html = f"<div class='card' style='border-left-color:#7c3aed;'><b>Test Case:</b> {case.title()}<br><b>Req ID:</b> REQ_{i+1:03d}<br>"
                if req:
                    html += f"<b>Description:</b> {req['requirement']}<br><b>Equipment:</b> {', '.join(req['equipment'])}"
                else:
                    html += "<b>Description:</b> Generic requirement - system must be tested."
                st.markdown(html + "</div>", unsafe_allow_html=True)

elif option == "Component Information":
    st.subheader("Key Component Information", anchor=False)
    st.caption("Look up parts from the detailed component database.")
    
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., gcm155l81e104ke02d").lower().strip()
    
    if st.button("Find Component"):
        if part_q:
            result = UNIFIED_COMPONENT_DB.get(part_q)
            if result:
                st.session_state.found_component = result
                st.success(f"Found: {part_q.upper()}. Displaying details below.")
            else:
                st.session_state.found_component = None
                st.warning("Part number not found in the internal database.")
    
    if st.session_state.found_component:
        st.markdown("---")
        component = st.session_state.found_component
        st.markdown(f"### Details for: {part_q.upper()}")
        
        # Filter out keys with no meaningful value before displaying
        display_data = {k.replace('_', ' ').title(): v for k, v in component.items() if pd.notna(v)}
        
        data_items = list(display_data.items())
        
        col1, col2 = st.columns(2)
        
        midpoint = len(data_items) // 2 + (len(data_items) % 2)
        
        with col1:
            for key, value in data_items[:midpoint]:
                st.markdown(f"<span class='component-label'>{key}:</span> <span class='component-value'>{value}</span>", unsafe_allow_html=True)
        
        with col2:
            for key, value in data_items[midpoint:]:
                st.markdown(f"<span class='component-label'>{key}:</span> <span class='component-value'>{value}</span>", unsafe_allow_html=True)

else: # Dashboard
    st.subheader("Dashboard & Analytics", anchor=False)
    st.caption("High-level view of session activities.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.reports_verified)
    c2.metric("Requirements Generated", st.session_state.requirements_generated)
    c3.metric("Components in Temp DB", len(st.session_state.component_db))
