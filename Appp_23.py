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
    # VCU, Motor Controller, Charger, BMS
    "spc560p50l3": {"Subsystem": "VCU", "Part Name": "32-bit MCU", "Manufacturer": "STMicroelectronics", "Qualification": "AEC-Q100"},
    "tja1051t": {"Subsystem": "VCU", "Part Name": "CAN Transceiver", "Manufacturer": "NXP", "Qualification": "AEC-Q100"},
    "tle4275g": {"Subsystem": "VCU", "Part Name": "5V LDO Regulator", "Manufacturer": "Infineon", "Qualification": "AEC-Q100"},
    "fsbb30ch60f": {"Subsystem": "Motor Controller", "Part Name": "IGBT Module", "Manufacturer": "ON Semi"},
    "wslp2512r0100fe": {"Subsystem": "Motor Controller", "Part Name": "Current Sense Resistor", "Manufacturer": "Vishay"},
    "bq76952": {"Subsystem": "BMS", "Part Name": "Battery Monitor", "Manufacturer": "Texas Instruments"},
    
    # General Purpose Components
    "irfz44n": {"Subsystem": "General", "Part Name": "MOSFET", "Manufacturer": "Infineon"},
    "1n4007": {"Subsystem": "General", "Part Name": "Diode", "Manufacturer": "Multiple"},
    "fh28-10s-0.5sh(05)": {"Manufacturer": "Hirose Electric Co Ltd", "Part Name": "Connector", "Subsystem": "General"},
    "gcm155l81e104ke02d": {"Manufacturer": "Murata", "Product Category": "MLCC - SMD/SMT", "Capacitance": "0.1 uF", "Voltage Rating DC": "25 VDC", "Dielectric": "X8L", "Tolerance": "10 %", "Case Code": "0402", "Min Temp": "-55 C", "Max Temp": "+150 C", "Qualification": "AEC-Q200"},
    "cga3e3x7s1a225k080ae": {"Manufacturer": "TDK", "Product Category": "MLCC - SMD/SMT", "Capacitance": "2.2 uF", "Voltage Rating DC": "10 VDC", "Dielectric": "X7S", "Tolerance": "10 %", "Case Code": "0603", "Qualification": "AEC-Q200"},
    "grt1555c1e220ja02j": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "grt155r61a475me13d": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "grt31cr61a476ke13l": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "cga3e1x7r1e105k080ac": {"Manufacturer": "TDK Corporation", "Part Name": "Capacitor", "Subsystem": "General"},
    "cga2b2c0g1h180j050ba": {"Manufacturer": "TDK Corporation", "Part Name": "Capacitor", "Subsystem": "General"},
    "c0402c103k4racauto": {"Manufacturer": "KEMET", "Part Name": "Capacitor", "Subsystem": "General"},
    "gcm1555c1h101ja16d": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "grt155r71h104ke01d": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "grt21br61e226me13l": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "grt1555c1h150fa02d": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "0402yc222j4t2a": {"Manufacturer": "KYOCERA AVX", "Part Name": "Capacitor", "Subsystem": "General"},
    "gcm1555c1h560fa16d": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "grt1555c1h330fa02d": {"Manufacturer": "Murata Electronics North America", "Part Name": "Capacitor", "Subsystem": "General"},
    "grt188c81a106me13d": {"Manufacturer": "Murata Electronics North America", "Part Name": "Capacitor", "Subsystem": "General"},
    "umk212b7105kght": {"Manufacturer": "Taiyo Yuden", "Part Name": "Capacitor", "Subsystem": "General"},
    "c1206c104k5racauto": {"Manufacturer": "KEMET", "Part Name": "Capacitor", "Subsystem": "General"},
    "grt31cr61h106ke01k": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "mcasu105sb7103kfna01": {"Manufacturer": "Taiyo Yuden", "Part Name": "Capacitor", "Subsystem": "General"},
    "c0402c333k4racauto": {"Manufacturer": "KEMET", "Part Name": "Capacitor", "Subsystem": "General"},
    "cl10b474ko8vpnc": {"Manufacturer": "Samsung Electro-Mechanics", "Part Name": "Capacitor", "Subsystem": "General"},
    "gcm155r71c224ke02d": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "gcm155r71h102ka37j": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "50tpv330m10x10.5": {"Manufacturer": "Rubycon", "Part Name": "Capacitor", "Subsystem": "General"},
    "cl31b684kbhwpne": {"Manufacturer": "Samsung Electro-Mechanics", "Part Name": "Capacitor", "Subsystem": "General"},
    "gcm155r71h272ka37d": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "edk476m050s9haa": {"Manufacturer": "KEMET", "Part Name": "Capacitor", "Subsystem": "General"},
    "gcm155r71h332ka37j": {"Manufacturer": "Murata Electronics", "Part Name": "Capacitor", "Subsystem": "General"},
    "a768ke336m1hlae042": {"Manufacturer": "KEMET", "Part Name": "Capacitor", "Subsystem": "General"},
    "ac0402jrx7r9bb152": {"Manufacturer": "YAGEO", "Part Name": "Resistor", "Subsystem": "General"},
    "d5v0h1b2lpq-7b": {"Manufacturer": "Diodes Incorporated", "Part Name": "Diode", "Subsystem": "General"},
    "szmmbz9v1alt3g": {"Manufacturer": "onsemi", "Part Name": "Diode", "Subsystem": "General"},
    "d24v0s1u2tq-7": {"Manufacturer": "Diodes Incorporated", "Part Name": "Diode", "Subsystem": "General"},
    "b340bq-13-f": {"Manufacturer": "Diodes Incorporated", "Part Name": "Diode", "Subsystem": "General"},
    "tld8s22ah": {"Manufacturer": "Taiwan Semiconductor", "Part Name": "Diode", "Subsystem": "General"},
    "b260aq-13-f": {"Manufacturer": "Diodes Incorporated", "Part Name": "Diode", "Subsystem": "General"},
    "rb530sm-40fht2r": {"Manufacturer": "Rohm Semiconductor", "Part Name": "Diode", "Subsystem": "General"},
    "74279262": {"Manufacturer": "Würth Elektronik", "Part Name": "Ferrite Bead", "Subsystem": "General"},
    "742792641": {"Manufacturer": "Würth Elektronik", "Part Name": "Ferrite Bead", "Subsystem": "General"},
    "742792625": {"Manufacturer": "Würth Elektronik", "Part Name": "Ferrite Bead", "Subsystem": "General"},
    "742792150": {"Manufacturer": "Würth Elektronik", "Part Name": "Ferrite Bead", "Subsystem": "General"},
    "78279220800": {"Manufacturer": "Würth Elektronik", "Part Name": "Ferrite Bead", "Subsystem": "General"},
    "voma617a-4x001t": {"Manufacturer": "Vishay Semiconductor Opto Division", "Part Name": "Optocoupler", "Subsystem": "General"},
    "534260610": {"Manufacturer": "Molex", "Part Name": "Connector", "Subsystem": "General"},
    "fh52-40s-0.5sh(99)": {"Manufacturer": "Hirose Electric Co Ltd", "Part Name": "Connector", "Subsystem": "General"},
    "x8821wv-06l-n0sn": {"Manufacturer": "XKB", "Part Name": "Connector", "Subsystem": "General"},
    "744235510": {"Manufacturer": "Würth Elektronik", "Part Name": "Inductor", "Subsystem": "General"},
    "lqw15an56nj8zd": {"Manufacturer": "Murata Electronics", "Part Name": "Inductor", "Subsystem": "General"},
    "spm7054vt-220m-d": {"Manufacturer": "TDK Corporation", "Part Name": "Inductor", "Subsystem": "General"},
    "744273801": {"Manufacturer": "Wurth Electronics Inc", "Part Name": "Inductor", "Subsystem": "General"},
    "74404084068": {"Manufacturer": "Würth Elektronik", "Part Name": "Inductor", "Subsystem": "General"},
    "744231091": {"Manufacturer": "Würth Elektronik", "Part Name": "Inductor", "Subsystem": "General"},
    "mlz2012m6r8htd25": {"Manufacturer": "TDK Corporation", "Part Name": "Inductor", "Subsystem": "General"},
    "rq3g270bjfratcb": {"Manufacturer": "Rohm Semiconductor", "Part Name": "MOSFET", "Subsystem": "General"},
    "pja138k-au_r1_000a1": {"Manufacturer": "Panjit International Inc.", "Part Name": "MOSFET", "Subsystem": "General"},
    "dmp2070uq-7": {"Manufacturer": "Diodes Incorporated", "Part Name": "MOSFET", "Subsystem": "General"},
    "ac0402jr-070rl": {"Manufacturer": "YAGEO", "Part Name": "Resistor", "Subsystem": "General"},
    "ac0402fr-07100kl": {"Manufacturer": "YAGEO", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0402ft158k": {"Manufacturer": "Stackpole Electronics Inc", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0402ft30k0": {"Manufacturer": "Stackpole Electronics Inc", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0402ft127k": {"Manufacturer": "Stackpole Electronics Inc", "Part Name": "Resistor", "Subsystem": "General"},
    "rmc10k204fth": {"Manufacturer": "KAMAYA", "Part Name": "Resistor", "Subsystem": "General"},
    "erj-2rkf2201x": {"Manufacturer": "Panasonic Electronic Components", "Part Name": "Resistor", "Subsystem": "General"},
    "erj-2rkf1002x": {"Manufacturer": "Panasonic Electronic Components", "Part Name": "Resistor", "Subsystem": "General"},
    "wr04x1004ftl": {"Manufacturer": "Walsin Technology Corporation", "Part Name": "Resistor", "Subsystem": "General"},
    "wr04x10r0ftl": {"Manufacturer": "Walsin Technology Corporation", "Part Name": "Resistor", "Subsystem": "General"},
    "rc0603fr-0759rl": {"Manufacturer": "YAGEO", "Part Name": "Resistor", "Subsystem": "General"},
    "rmc1/16jptp": {"Manufacturer": "Kamaya Inc.", "Part Name": "Resistor", "Subsystem": "General"},
    "ac0402fr-07100rl": {"Manufacturer": "YAGEO", "Part Name": "Resistor", "Subsystem": "General"},
    "ac0402fr-076k04l": {"Manufacturer": "YAGEO", "Part Name": "Resistor", "Subsystem": "General"},
    "ac0402fr-07510rl": {"Manufacturer": "YAGEO", "Part Name": "Resistor", "Subsystem": "General"},
    "crgcq0402f56k": {"Manufacturer": "TE Connectivity Passive Product", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0402ft24k9": {"Manufacturer": "Stackpole Electronics Inc", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0402ft5k36": {"Manufacturer": "Stackpole Electronics Inc", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0603ft12k0": {"Manufacturer": "Stackpole Electronics Inc", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0402ft210k": {"Manufacturer": "Stackpole Electronics Inc", "Part Name": "Resistor", "Subsystem": "General"},
    "ltr18ezpfsr015": {"Manufacturer": "Rohm Semiconductor", "Part Name": "Resistor", "Subsystem": "General"},
    "erj-pa2j102x": {"Manufacturer": "Panasonic Electronic Components", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0402ft5k10": {"Manufacturer": "Stackpole Electronics Inc", "Part Name": "Resistor", "Subsystem": "General"},
    "rmcf0603ft100r": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "ac0402jr-074k7l": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "crf0805-fz-r010elf": {"manufacturer": "Bourns Inc.", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft3k16": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft3k48": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft1k50": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft4k02": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf1206zt0r00": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "rmcf0402ft402k": {"manufacturer": "Stackpole Electronics Inc", "part_name": "Resistor", "subsystem": "General"},
    "ac0603fr-7w20kl": {"manufacturer": "YAGEO", "part_name": "Resistor", "subsystem": "General"},
    "h164yp": {"manufacturer": "AGENEW", "part_name": "Unknown", "subsystem": "General"},
    "zldo1117qg33ta": {"manufacturer": "Diodes Incorporated", "part_name": "LDO Regulator", "subsystem": "General"},
    "ap63357qzv-7": {"manufacturer": "Diodes Incorporated", "part_name": "Switching Regulator", "subsystem": "General"},
    "pca9306idcurq1": {"manufacturer": "Texas Instruments", "part_name": "Level Translator", "subsystem": "General"},
    "mcp2518fdt-e/sl": {"manufacturer": "Microchip Technology", "part_name": "CAN Controller", "subsystem": "General"},
    "iso1042bqdwvq1": {"manufacturer": "Texas Instruments", "part_name": "CAN Transceiver", "subsystem": "General"},
    "pesd2canfd27v-tr": {"manufacturer": "Nexperia USA Inc.", "part_name": "ESD Protection", "subsystem": "General"},
    "lt8912b": {"manufacturer": "Lontium", "part_name": "MIPI DSI/CSI-2 Bridge", "subsystem": "General"},
    "sn74lv1t34qdckrq1": {"manufacturer": "Texas Instruments", "part_name": "Buffer", "subsystem": "General"},
    "ncp164csnadjt1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator", "subsystem": "General"},
    "20279-001e-03": {"manufacturer": "I-PEX", "part_name": "Connector", "subsystem": "General"},
    "ncv8161asn180t1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator", "subsystem": "General"},
    "drtr5v0u2sr-7": {"manufacturer": "Diodes Incorporated", "part_name": "ESD Protection", "subsystem": "General"},
    "ncv8161asn330t1g": {"manufacturer": "onsemi", "part_name": "LDO Regulator", "subsystem": "General"},
    "ecmf04-4hswm10y": {"manufacturer": "STMicroelectronics", "part_name": "Common Mode Filter", "subsystem": "General"},
    "nxs0102dc-q100h": {"manufacturer": "Nexperia USA Inc.", "part_name": "Level Translator", "subsystem": "General"},
    "cf0505xt-1wr3": {"manufacturer": "MORNSUN", "part_name": "DC/DC Converter", "subsystem": "General"},
    "iam-20680ht": {"manufacturer": "TDK InvenSense", "part_name": "IMU Sensor", "subsystem": "General"},
    "attiny1616-szt-vao": {"manufacturer": "Microchip", "part_name": "MCU", "subsystem": "General"},
    "tlv9001qdckrq1": {"manufacturer": "Texas Instruments", "part_name": "Op-Amp", "subsystem": "General"},
    "qmc5883l": {"manufacturer": "QST", "part_name": "Magnetometer", "subsystem": "General"},
    "lm76202qpwprq1": {"manufacturer": "Texas Instruments", "part_name": "Ideal Diode Controller", "subsystem": "General"},
    "bd83a04efv-me2": {"manufacturer": "Rohm Semiconductor", "part_name": "LED Driver", "subsystem": "General"},
    "ecs-200-12-33q-jes-tr": {"manufacturer": "ECS Inc.", "part_name": "Crystal", "subsystem": "General"},
    "ecs-250-12-33q-jes-tr": {"manufacturer": "ECS Inc.", "part_name": "Crystal", "subsystem": "General"},
    "aggbp.25a.07.0060a": {"manufacturer": "Toaglas", "part_name": "GNSS Antenna", "subsystem": "General"},
    "y4ete00a0aa": {"manufacturer": "Quectel", "part_name": "LTE Module", "subsystem": "General"},
    "yf0023aa": {"manufacturer": "Quectel", "part_name": "Wi-Fi/BT Antenna", "subsystem": "General"},
    "mb9df125": {"subsystem": "Instrument Cluster", "part_name": "MCU with Graphics", "manufacturer": "Spansion (Cypress)"},
    "veml6031x00": {"subsystem": "ALS Board", "part_name": "Ambient Light Sensor", "manufacturer": "Vishay"},
    "01270019-00": {"subsystem": "VIC Module", "part_name": "ANTENNA GPS", "manufacturer": "Unknown"},
    "01270020-00": {"subsystem": "VIC Module", "part_name": "ANTENNA WIFI", "manufacturer": "Unknown"},
    "01270021-00": {"subsystem": "VIC Module", "part_name": "ANTENNA LTE", "manufacturer": "Unknown"},
    "p0024-03": {"subsystem": "VIC Module", "part_name": "PCBA BOARD", "manufacturer": "Unknown"},
    "01270018-00": {"subsystem": "VIC Module", "part_name": "SENSOR ALS-PCBA", "manufacturer": "Unknown"},
    "01270010-02": {"subsystem": "VIC Module", "part_name": "TFT LCD WITH COVER GLASS", "manufacturer": "Unknown"},
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

        match_found = False
        for i, p in enumerate(patterns):
            match = re.match(p, line, re.I)
            if match:
                groups = match.groups()
                if i == 0:
                    test_data.update({"TestName": groups[0].strip(), "Result": "PASS" if groups[1].lower() in ["passed", "success"] else "FAIL", "Actual": groups[2].strip()})
                elif i == 1:
                    result_str = groups[1].lower()
                    result = "PASS" if "passed" in result_str or "success" in result_str else "FAIL" if "failed" in result_str else "INFO"
                    test_data.update({"TestName": groups[0].strip(), "Result": result, "Actual": groups[1].strip()})
                elif i == 2:
                     test_data.update({"TestName": groups[0].replace("_", " ").strip(), "Result": groups[1].upper()})
                elif i == 3:
                    test_data.update({"TestName": groups[0].strip(), "Result": "PASS" if groups[1].lower() in ["success", "passed"] else "FAIL"})
                elif i == 4:
                    test_data.update({"TestName": groups[0].strip(), "Result": "PASS" if groups[1].lower() == "passed" else "FAIL"})
                
                match_found = True
                break
        
        if match_found:
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
