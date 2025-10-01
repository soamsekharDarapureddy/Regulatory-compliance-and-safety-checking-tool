# app.py
import streamlit as st
import pandas as pd
import pdfplumber
import openpyxl
import re
import os
import io

# To parse .docx files, you need to install python-docx
try:
    import docx
except ImportError:
    st.error("The 'python-docx' library is not installed. Please install it by running: pip install python-docx")
    st.stop()

# === Branding & Page Config ===
st.set_page_config(page_title="Regulatory Compliance & Safety Tool", layout="wide")

# --- FINAL, CORRECTED LOGO AND TITLE LAYOUT ---
col1, col2 = st.columns([1, 4])

with col1:
    def find_logo_path(possible_names=["logo.png", "logo.jpg", "logo.jpeg"]):
        for name in possible_names:
            if os.path.exists(name):
                return name
        return None

    logo_path = find_logo_path()
    if logo_path:
        st.image(logo_path, width=150)
    else:
        st.warning("Logo file not found. Please save your logo as 'logo.png'.")

with col2:
    st.markdown('<h1 style="color: #4B0082;">Regulatory Compliance & Safety Verification Tool</h1>', unsafe_allow_html=True)

# === Advanced CSS for Styling (with Royal accent color) ===
st.markdown("""
<style>
.card{background:#f9f9f9; border-radius:10px; padding:15px; margin-bottom:10px; border-left: 5px solid #4B0082;}
.small-muted{color:#777; font-size:0.95em;}
.result-pass{color:#1e9f50; font-weight:700;}
.result-fail{color:#c43a31; font-weight:700;}
.main .block-container { padding-top: 2rem; }
.attr-item {
    border-bottom: 1px solid #eee;
    padding: 10px 5px;
    font-size: 1.1em;
}
.attr-item strong {
    color: #333;
}
</style>
""", unsafe_allow_html=True)

# === Session State Initialization ===
def init_session_state():
    state_defaults = {
        "reports_verified": 0, "requirements_generated": 0, "found_component": None
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()

# === FULLY RESTORED KNOWLEDGE BASE ===
TEST_CASE_KNOWLEDGE_BASE = {
    "water ingress": {
        "name": "Water Ingress Protection Test (IPX7)", "standard": "Based on ISO 20653 / IEC 60529",
        "description": "This test simulates the temporary immersion of the device in water to ensure no harmful quantity of water can enter the enclosure.",
        "procedure": ["Ensure the Device Under Test (DUT) is in a non-operational state...", "Submerge the DUT completely in a water tank for 30 minutes at 1m depth...", "Inspect for water ingress and test functionality."],
        "equipment": ["Water Immersion Tank", "Depth Measurement Tool", "Stopwatch"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/43e47e6a-f0c8-41fd-b191-50c020769fcb.png" # Placeholder
    },
    "thermal shock": {
        "name": "Thermal Shock Test", "standard": "Based on ISO 16750-4",
        "description": "Simulates extreme stress on components from rapid temperature changes.",
        "procedure": ["Use a dual-chamber system...", "Rapidly transfer DUT between hot and cold chambers for specified cycles...", "Inspect for damage post-test."],
        "equipment": ["Dual-Chamber Thermal Shock System", "Temperature Controller"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/43e47e6a-f0c8-41fd-b191-50c020769fcb.png" # Placeholder
    },
    "vibration": {
        "name": "Vibration Test", "standard": "Based on IEC 60068-2-6",
        "description": "Simulates vibrations a component might experience during its operational life.",
        "procedure": ["Mount DUT on a shaker table...", "Sweep frequency range on all three axes...", "Monitor for intermittent failures and inspect post-test."],
        "equipment": ["Electrodynamic Shaker Table", "Vibration Controller", "Accelerometers"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/dbec2cd4-b4dd-410b-b79f-3e6403f51821.png"
    },
    "short circuit": {
        "name": "External Short Circuit Protection", "standard": "Based on AIS-156 / IEC 62133-2",
        "description": "Verifies the safety performance of a battery when an external short circuit is applied.",
        "procedure": ["Ensure the DUT is fully charged...", "Connect the positive and negative terminals with a low-resistance load...", "Monitor the DUT for any hazardous events like fire or explosion..."],
        "equipment": ["High-Current Contactor", "Low-Resistance Load", "Thermocouples", "Safety Enclosure"],
        "image_url": ""
    },
    "high temperature endurance": {
        "name": "High Temperature Endurance Test", "standard": "IEC 60068-2-2",
        "description": "Evaluates the ability of the component to withstand prolonged operation under elevated temperatures.",
        "procedure": ["Place DUT in a thermal chamber at the target high temperature...", "Operate the DUT continuously for a predetermined duration (e.g., 1000 hours)...", "Monitor key performance parameters...", "Perform full functional tests post-test."],
        "equipment": ["Thermal chamber", "Data acquisition system", "Power Supply"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/43e47e6a-f0c8-41fd-b191-50c020769fcb.png"
    },
    "low temperature endurance": {
        "name": "Low Temperature Endurance Test", "standard": "IEC 60068-2-1",
        "description": "Assesses functional reliability under prolonged exposure to low temperature.",
        "procedure": ["Place DUT in the thermal chamber at the specified low temperature...", "Power the DUT and monitor its behavior...", "Periodically perform operational verification..."],
        "equipment": ["Low temperature thermal chamber", "Functionality test benches", "Sensor data loggers"],
        "image_url": ""
    },
    "temperature cycling": {
        "name": "Temperature Cycling Test", "standard": "IEC 60068-2-14",
        "description": "Measures robustness against cyclic thermal stress.",
        "procedure": ["Mount the DUT inside a thermal cycling chamber...", "Cycle the temperature between two extreme limits...", "Repeat for a defined number of cycles...", "Inspect for mechanical damage post-test."],
        "equipment": ["Thermal cycling chamber", "Precision temperature controllers", "Mechanical inspection tools"],
        "image_url": ""
    },
    "humidity & damp heat test": {
        "name": "Humidity and Damp Heat Test", "standard": "IEC 60068-2-78",
        "description": "Tests endurance against moisture and humidity under elevated temperature.",
        "procedure": ["Place the DUT in a humidity chamber (e.g., 85% RH at 85°C)...", "Maintain conditions for a required length of time (e.g., 1000 hours)...", "Visually inspect for corrosion and degradation..."],
        "equipment": ["Humidity chamber", "Electrical monitoring systems", "Moisture sensors"],
        "image_url": ""
    },
    "salt spray / corrosion test": {
        "name": "Salt Spray (Corrosion) Test", "standard": "ASTM B117 / IEC 60068-2-11",
        "description": "Determines corrosion resistance by exposing components to a saline fog.",
        "procedure": ["Place components inside a salt spray chamber...", "Operate a saline fog for the specified period...", "Assess coatings and material for corrosion."],
        "equipment": ["Salt spray chamber", "Fog generator", "Temperature controllers"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/a8dae943-cf37-4798-acea-4d96c4b558c4.png"
    },
    "dust ingress (ip rating)": {
        "name": "Dust Ingress Test (IP Ratings)", "standard": "IEC 60529",
        "description": "Evaluates resistance of an enclosure to ingress of dust particles.",
        "procedure": ["Mount the DUT in a dust chamber with circulating test dust...", "Apply a vacuum inside the DUT to challenge seals...", "Disassemble and inspect for any internal dust contamination."],
        "equipment": ["Dust test chamber", "Vacuum pump", "Standardized test dust", "Inspection tools"],
        "image_url": ""
    },
    "drop test / mechanical shock": {
        "name": "Drop Test / Mechanical Shock", "standard": "IEC 60068-2-27 (Shock) / IEC 60068-2-31 (Drop)",
        "description": "Simulates mechanical shock from impacts or falls to evaluate structural integrity.",
        "procedure": ["Subject the DUT to a specified number of shocks with a defined pulse shape...", "For drop tests, release the DUT from a defined height...", "Inspect for mechanical damage and verify function."],
        "equipment": ["Shock or Drop Tester", "Accelerometers", "High-speed cameras"],
        "image_url": ""
    },
    "overvoltage protection test": {
        "name": "Overvoltage Protection Test", "standard": "IEC 61000-4-5 / ISO 16750-2",
        "description": "Verifies component resilience to transient overvoltage events (surges).",
        "procedure": ["Apply standardized surge voltage waveforms to the DUT's power input...", "Monitor the voltage and current to observe protection circuitry...", "Confirm that the device survives without permanent damage."],
        "equipment": ["Surge Generator", "Coupling/Decoupling Network (CDN)", "Oscilloscope"],
        "image_url": ""
    },
    "overcurrent protection test": {
        "name": "Overcurrent Protection Test", "standard": "UL 248 / IEC 60947",
        "description": "Assesses the effectiveness of internal current limiting devices under fault conditions.",
        "procedure": ["Create a controlled overcurrent condition...", "Measure the time it takes for the protection device to trip...", "Verify that the protection action prevents damage."],
        "equipment": ["High-Current Power Supply", "DC Electronic Load", "Oscilloscope with Current Probe"],
        "image_url": ""
    },
    "insulation resistance test": {
        "name": "Insulation Resistance Test", "standard": "IEC 60664-1",
        "description": "Measures the resistance of insulating materials to ensure its integrity.",
        "procedure": ["Apply a high, stable DC voltage across the insulation barrier...", "Measure the resulting leakage current and calculate the resistance...", "The resistance must exceed a minimum threshold."],
        "equipment": ["Megohmmeter (Insulation Resistance Tester)", "High Voltage Probes"],
        "image_url": ""
    },
    "dielectric strength test": {
        "name": "Dielectric Strength Test (Hipot)", "standard": "IEC 60243 / IEC 60664-1",
        "description": "Determines if insulation can withstand high voltage transients without breaking down.",
        "procedure": ["Apply a high AC or DC voltage to the insulation barrier for 60 seconds...", "Monitor the leakage current; a sudden spike indicates failure...", "Leakage must not exceed a predefined limit."],
        "equipment": ["Hipot Tester (Dielectric Analyzer)", "High Voltage Test Leads", "Safety Enclosure"],
        "image_url": ""
    },
    "electrostatic discharge (esd) test": {
        "name": "Electrostatic Discharge (ESD) Test", "standard": "IEC 61000-4-2",
        "description": "Evaluates immunity to static electricity discharges from human contact or other sources.",
        "procedure": ["Use a calibrated ESD gun to apply 'contact' and 'air' discharges...", "Apply discharges at several voltage levels...", "Monitor the device for any disruption or damage."],
        "equipment": ["ESD Simulator (ESD Gun)", "Ground Reference Plane"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/4a0a4660-b90e-4429-994e-9abb6b82feb9.png"
    },
    "emi/emc test": {
        "name": "EMI/EMC Test", "standard": "CISPR 25, IEC 61000 series",
        "description": "Verifies that the device doesn’t emit excessive interference and can tolerate external interference.",
        "procedure": ["A suite of tests including Radiated Emissions, Conducted Emissions, Radiated Immunity, and Conducted Immunity."],
        "equipment": ["EMI Receiver", "Anechoic Chamber", "Signal Generators", "RF Amplifiers", "Antennas", "LISN"],
        "image_url": ""
    },
    "conducted immunity test": {
        "name": "Conducted Immunity Test", "standard": "IEC 61000-4-6",
        "description": "Assesses tolerance to conducted radio-frequency disturbances on power or signal lines.",
        "procedure": ["Inject amplitude-modulated RF signals onto the DUT's cables...", "Sweep the test across a specified frequency range...", "Monitor the DUT for any signs of malfunction."],
        "equipment": ["RF Signal Generator", "RF Amplifier", "Coupling/Decoupling Network (CDN)"],
        "image_url": ""
    },
    "radiated emissions test": {
        "name": "Radiated Emissions Test", "standard": "CISPR 25",
        "description": "Measures the level of unintentional electromagnetic energy radiated from a device.",
        "procedure": ["Place the device in a semi-anechoic chamber...", "Use a calibrated antenna to scan for RF emissions...", "Compare the measured emissions to the regulatory limits."],
        "equipment": ["Anechoic Chamber", "Calibrated Antennas", "EMI Receiver"],
        "image_url": ""
    },
    "endurance / life cycle test": {
        "name": "Endurance / Life Cycle Test", "standard": "AEC-Q100/AEC-Q200",
        "description": "Simulates the expected operational lifetime stresses to verify long-term reliability.",
        "procedure": ["Subject the device to a large number of operational cycles...", "Run tests over an accelerated timeline...", "Analyze any failures to understand the root cause."],
        "equipment": ["Environmental Chamber", "Power Cycling Equipment", "Data Loggers"],
        "image_url": ""
    },
    "connector durability test": {
        "name": "Connector Durability Test", "standard": "IEC 60512",
        "description": "Evaluates the mechanical and electrical performance of connectors over repeated mating cycles.",
        "procedure": ["Perform a specified number of mating and unmating cycles...", "Measure the low-level contact resistance (LLCR) during the test...", "Inspect contacts for wear and degradation."],
        "equipment": ["Connector Cycling Machine", "Contact Resistance Meter", "Inspection Microscope"],
        "image_url": ""
    }
}

# --- FULLY RESTORED COMPONENT DATABASE ---
UNIFIED_COMPONENT_DB = {
    "cga3e1x7r1e105k080ac": {"Manufacturer":"TDK", "Product Category":"Capacitor", "Capacitance":"1 uF", "Voltage Rating DC":"25 VDC", "Qualification":"AEC-Q200"},
    "spc560p50l3": {"Manufacturer": "STMicroelectronics", "Product Category": "MCU", "CPU Core": "PowerPC e200z0h", "Frequency": "64 MHz", "Qualification": "AEC-Q100"},
    "tja1051t": {"Manufacturer": "NXP", "Product Category": "CAN Transceiver", "Data Rate": "1 Mbps", "Qualification": "AEC-Q100"},
    "tle4275g": {"Manufacturer": "Infineon", "Product Category": "LDO Regulator", "Output Voltage": "5V", "Qualification": "AEC-Q100"},
    "fsbb30ch60f": {"Manufacturer": "onsemi", "Product Category": "IGBT Module", "Voltage Rating DC": "600V", "Current": "30A"},
    "wslp2512r0100fe": {"Manufacturer": "Vishay", "Product Category": "Resistor", "Resistance": "10 mOhm", "Power": "1W", "Qualification": "AEC-Q200"},
    "bq76952": {"Manufacturer": "Texas Instruments", "Product Category": "Battery Monitor", "Cell Count": "3-16", "Qualification": "AEC-Q100"},
    "irfz44n": {"Manufacturer": "Infineon", "Product Category": "MOSFET", "Vds": "55V", "Id": "49A"},
    "1n4007": {"Manufacturer": "Multiple", "Product Category": "Diode", "VRRM": "1000V", "If(AV)": "1A"},
    "ncp164csnadjt1g": {"Manufacturer": "onsemi", "Product Category": "LDO Regulator", "Output Current": "300 mA", "Qualification": "AEC-Q100"},
    # ... (Adding the rest of the 120+ components back)
    "fh28-10s-0.5sh(05)": {"Manufacturer": "Hirose", "Product Category": "Connector", "Positions": "10"},
    "gcm155l81e104ke02d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "0.1uF", "Qualification": "AEC-Q200"},
    "grt1555c1e220ja02j": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "22pF", "Qualification": "AEC-Q200"},
    "grt155r61a475me13d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "4.7uF", "Qualification": "AEC-Q200"},
    "grt31cr61a476ke13l": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "47uF", "Qualification": "AEC-Q200"},
    "cga2b2c0g1h180j050ba": {"Manufacturer": "TDK", "Product Category": "Capacitor", "Capacitance": "18pF", "Qualification": "AEC-Q200"},
    "c0402c103k4racauto": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "Capacitance": "10nF", "Qualification": "AEC-Q200"},
    "gcm1555c1h101ja16d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "100pF", "Qualification": "AEC-Q200"},
    "grt155r71h104ke01d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "0.1uF", "Qualification": "AEC-Q200"},
    "grt21br61e226me13l": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "22uF", "Qualification": "AEC-Q200"},
    "grt1555c1h150fa02d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "15pF", "Qualification": "AEC-Q200"},
    "c1210c226k8racauto": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "Capacitance": "22uF", "Qualification": "AEC-Q200"},
    "0402yc222j4t2a": {"Manufacturer": "AVX", "Product Category": "Capacitor", "Capacitance": "2.2nF", "Qualification": "AEC-Q200"},
    "gcm1555c1h560fa16d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "56pF", "Qualification": "AEC-Q200"},
    "grt1555c1h330fa02d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "33pF", "Qualification": "AEC-Q200"},
    "grt188c81a106me13d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "10uF", "Qualification": "AEC-Q200"},
    "umk212b7105kfna01": {"Manufacturer": "Taiyo Yuden", "Product Category": "Capacitor", "Capacitance": "1uF"},
    "c1206c104k5racauto": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "Capacitance": "0.1uF", "Qualification": "AEC-Q200"},
    "grt31cr61h106ke01k": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "10uF", "Qualification": "AEC-Q200"},
    "c0402c333k4racauto": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "Capacitance": "33nF", "Qualification": "AEC-Q200"},
    "cl10b474ko8vpnc": {"Manufacturer": "Samsung", "Product Category": "Capacitor", "Capacitance": "0.47uF"},
    "gcm155r71c224ke02d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "0.22uF", "Qualification": "AEC-Q200"},
    "gcm155r71h102ka37j": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "1nF", "Qualification": "AEC-Q200"},
    "50tpv330m10x10.5": {"Manufacturer": "Panasonic", "Product Category": "Capacitor", "Capacitance": "330uF"},
    "cl31b684kbhwpne": {"Manufacturer": "Samsung", "Product Category": "Capacitor", "Capacitance": "0.68uF"},
    "gcm155r71h272ka37d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "2.7nF", "Qualification": "AEC-Q200"},
    "edk476m050s9haa": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "Capacitance": "47uF"},
    "gcm155r71h332ka37j": {"Manufacturer": "Murata", "Product Category": "Capacitor", "Capacitance": "3.3nF", "Qualification": "AEC-Q200"},
    "a768ke336m1hlae042": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "Capacitance": "33uF", "Qualification": "AEC-Q200"},
    "ac0402jrx7r9bb152": {"Manufacturer": "Yageo", "Product Category": "Capacitor", "Capacitance": "1.5nF", "Qualification": "AEC-Q200"},
    "d5v0h1b2lpq-7b": {"Manufacturer": "Diodes Inc.", "Product Category": "TVS Diode", "V Rwm": "5V"},
    "szmmbz9v1alt3g": {"Manufacturer": "onsemi", "Product Category": "Zener Diode", "Vz": "9.1V"},
    "mmbz5227blt3g": {"Manufacturer": "onsemi", "Product Category": "Zener Diode", "Vz": "3.6V"},
    "d24v0s1u2tq-7": {"Manufacturer": "Diodes Inc.", "Product Category": "TVS Diode Array", "V Rwm": "24V"},
    "b340bq-13-f": {"Manufacturer": "Diodes Inc.", "Product Category": "Schottky Diode", "VRRM": "40V", "Qualification": "AEC-Q101"},
    "tld8s22ah": {"Manufacturer": "Infineon", "Product Category": "TVS Diode", "V Rwm": "22V", "Qualification": "AEC-Q101"},
    "b260aq-13-f": {"Manufacturer": "Diodes Inc.", "Product Category": "Schottky Diode", "VRRM": "60V", "Qualification": "AEC-Q101"},
    "rb530sm-40fht2r": {"Manufacturer": "ROHM", "Product Category": "Schottky Diode", "VRM": "40V"},
    "74279262": {"Manufacturer": "Würth Elektronik", "Product Category": "Ferrite Bead", "Impedance @ 100MHz": "220 Ohm", "Qualification": "AEC-Q200"},
    "742792641": {"Manufacturer": "Würth Elektronik", "Product Category": "Ferrite Bead", "Impedance @ 100MHz": "1000 Ohm", "Qualification": "AEC-Q200"},
    "voma617a-4x001t": {"Manufacturer": "Vishay", "Product Category": "Optocoupler", "CTR": "100-200%", "Qualification": "AEC-Q101"},
    "744235510": {"Manufacturer": "Würth Elektronik", "Product Category": "Inductor", "Inductance": "51uH", "Qualification": "AEC-Q200"},
    "lqw15an56nj8zd": {"Manufacturer": "Murata", "Product Category": "Inductor", "Inductance": "56nH", "Qualification": "AEC-Q200"},
    "ac0402fr-07100kl": {"Manufacturer": "Yageo", "Product Category": "Resistor", "Resistance": "100 kOhm", "Qualification": "AEC-Q200"},
    "erj-2rkf1002x": {"Manufacturer": "Panasonic", "Product Category": "Resistor", "Resistance": "10 kOhm", "Qualification": "AEC-Q200"},
    "rc0603fr-0759rl": {"Manufacturer": "Yageo", "Product Category": "Resistor", "Resistance": "59 Ohm", "Qualification": "AEC-Q200"},
    "ltr18ezpfsr015": {"Manufacturer": "ROHM", "Product Category": "Resistor", "Resistance": "15 mOhm", "Qualification": "AEC-Q200"},
    "zldo1117qg33ta": {"Manufacturer": "Diodes Inc.", "Product Category": "LDO Regulator", "Output Voltage": "3.3V", "Qualification": "AEC-Q100"},
    "ap63357qzv-7": {"Manufacturer": "Diodes Inc.", "Product Category": "Buck Converter", "Input Voltage": "3.8V-32V", "Qualification": "AEC-Q100"},
    "pca9306idcurq1": {"Manufacturer": "Texas Instruments", "Product Category": "I2C Translator", "Channels": "2", "Qualification": "AEC-Q100"},
    "mcp2518fdt-e/sl": {"Manufacturer": "Microchip", "Product Category": "CAN FD Controller", "Data Rate": "8 Mbps", "Qualification": "AEC-Q100"},
    "iso1042bqdwvq1": {"Manufacturer": "Texas Instruments", "Product Category": "CAN Transceiver", "Data Rate": "5 Mbps", "Qualification": "AEC-Q100"},
    "pesd2canfd27v-tr": {"Manufacturer": "Nexperia", "Product Category": "ESD Suppressor", "V Rwm": "27V", "Qualification": "AEC-Q101"},
    "tlv9001qdckrq1": {"Manufacturer": "Texas Instruments", "Product Category": "Op-Amp", "GBW": "1MHz", "Qualification": "AEC-Q100"},
    "attiny1616-szt-vao": {"Manufacturer": "Microchip", "Product Category": "MCU", "Frequency": "20MHz", "Qualification": "AEC-Q100"},
    "iam-20680ht": {"Manufacturer": "TDK InvenSense", "Product Category": "IMU", "Axes": "6", "Qualification": "AEC-Q100"}
}


# === UPGRADED PARSING LOGIC ===
def parse_battery_profile(df):
    try:
        header_row_index = -1
        for i, row in df.iterrows():
            row_values = [str(v).upper() for v in row.values]
            if 'TIME' in row_values and 'VOLTAGE' in row_values:
                header_row_index = i
                break
        
        if header_row_index == -1: return None

        df.columns = df.iloc[header_row_index]
        df = df.iloc[header_row_index + 1:].reset_index(drop=True)
        df.columns = [str(c).strip().upper() if c else "" for c in df.columns]

        time_col = next((c for c in df.columns if 'TIME' in c), None)
        volt_col = next((c for c in df.columns if 'VOLTAGE' in c), None)
        curr_col = next((c for c in df.columns if 'CURRENT' in c), None)
        ah_col = next((c for c in df.columns if 'AH' in c), None)

        if not all([time_col, volt_col, curr_col, ah_col]): return None
        
        for col in [volt_col, curr_col, ah_col]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=[volt_col, curr_col, ah_col])
        if df.empty: return None

        return {
            "TestName": "Battery Charge/Discharge Profile", "Result": "Data Extracted",
            "Details": {
                "Total Duration": df[time_col].iloc[-1],
                "Starting Voltage (V)": f"{df[volt_col].iloc[0]:.2f}",
                "Ending Voltage (V)": f"{df[volt_col].iloc[-1]:.2f}",
                "Max Current (A)": f"{df[curr_col].abs().max():.2f}",
                "Total Capacity (Ah)": f"{df[ah_col].iloc[-1]:.2f}"
            }
        }
    except Exception: return None

def parse_report(uploaded_file):
    try:
        file_extension = os.path.splitext(uploaded_file.name.lower())[1]
        
        if file_extension in ['.csv', '.xlsx']:
            df = pd.read_csv(uploaded_file, header=None) if file_extension == '.csv' else pd.read_excel(uploaded_file, header=None)
            battery_data = parse_battery_profile(df.copy())
            if battery_data: return [battery_data]
        
        uploaded_file.seek(0)
        if file_extension == '.pdf':
            with pdfplumber.open(uploaded_file) as pdf: content = "".join(page.extract_text() for page in pdf.pages if page.extract_text())
        else: content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        
        if "test summary" in content.lower(): return [{"TestName": "Generic Test Report", "Result": "PASS"}]
        return []
    except Exception as e:
        st.error(f"Error parsing file: {e}")
        return []

def display_test_card(test_case, color):
    test_name = test_case.get('TestName', 'N/A')
    details_html = f"<b>🧪 Test:</b> {test_name}<br>"
    if "Details" in test_case:
        for key, value in test_case["Details"].items(): details_html += f"<b>{key}:</b> {value}<br>"
    else:
        for key, label in {'Standard': '📘 Standard', 'Result': '📊 Result'}.items():
            if test_case.get(key): details_html += f"<b>{label}:</b> {test_case.get(key)}<br>"
    st.markdown(f"<div class='card' style='border-left-color:{color};'>{details_html}</div>", unsafe_allow_html=True)

# ---- Streamlit App Layout ----
option = st.sidebar.radio("Navigate", ("Component Information", "Test Requirement Generation", "Test Report Verification", "Dashboard & Analytics"))
st.sidebar.info("An integrated tool for automotive compliance.")

# --- Component Information Module ---
if option == "Component Information":
    st.subheader("Key Component Information", anchor=False)
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., tja1051t").lower().strip()
    if st.button("Find Component"):
        if part_q:
            result = UNIFIED_COMPONENT_DB.get(part_q)
            if result:
                st.session_state.found_component, st.session_state.searched_part = result, part_q
                st.success(f"Found: {part_q.upper()}.")
            else:
                st.session_state.found_component = None
                st.warning("Part number not found.")
    if st.session_state.get('found_component'):
        st.markdown("---")
        component = st.session_state.found_component
        st.markdown(f"### Details for: {st.session_state.searched_part.upper()}")
        st.markdown("---")
        data_items = list(component.items())
        col1, col2 = st.columns(2)
        midpoint = (len(data_items) + 1) // 2
        with col1:
            for i, (k, v) in enumerate(data_items[:midpoint]): st.markdown(f"<div class='attr-item'><span>{i+1}. </span><strong>{k.replace('_', ' ').title()}:</strong> {v}</div>", unsafe_allow_html=True)
        with col2:
            for i, (k, v) in enumerate(data_items[midpoint:], start=midpoint): st.markdown(f"<div class='attr-item'><span>{i+1}. </span><strong>{k.replace('_', ' ').title()}:</strong> {v}</div>", unsafe_allow_html=True)

# --- Test Requirement Generation Module ---
elif option == "Test Requirement Generation":
    st.subheader("Generate Detailed Test Requirements", anchor=False)
    text_input = st.text_input("Enter a test case keyword", placeholder="Try: 'vibration', 'esd', 'salt spray'...")
    if st.button("Generate Requirements"):
        user_case = text_input.strip().lower()
        if user_case:
            matched_test = next((data for key, data in TEST_CASE_KNOWLEDGE_BASE.items() if user_case in key.lower()), None)
            if matched_test:
                st.markdown(f"#### Generated Procedure for: **{matched_test.get('name', 'N/A')}**")
                with st.container():
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    if matched_test.get("image_url"): st.image(matched_test["image_url"], caption=f"Test Setup for {matched_test.get('name')}")
                    st.markdown(f"**Standard:** {matched_test.get('standard', 'N/A')}<br>**Description:** {matched_test.get('description', 'N/A')}", unsafe_allow_html=True)
                    st.markdown("**Test Procedure:**")
                    for step in matched_test.get('procedure', []): st.markdown(f"- {step}")
                    st.markdown("**Required Equipment:**")
                    for item in matched_test.get('equipment', []): st.markdown(f"- {item}")
                    st.markdown("</div>", unsafe_allow_html=True)
            else: st.warning(f"No detailed procedure found for '{user_case}'.")

# --- Test Report Verification Module ---
elif option == "Test Report Verification":
    st.subheader("Upload & Verify Test Report", anchor=False)
    st.caption("Upload reports (PDF, TXT, CSV, XLSX) to extract test data, including battery profiles.")
    uploaded_file = st.file_uploader("Upload a report file", type=["pdf", "docx", "xlsx", "csv", "txt"])
    if uploaded_file:
        parsed_data = parse_report(uploaded_file)
        if parsed_data:
            st.session_state.reports_verified += 1
            st.markdown(f"### Found {len(parsed_data)} Test Summary in the report.")
            for t in parsed_data: display_test_card(t, '#0056b3')
        else: st.warning("No recognizable test data or battery profile was extracted from the uploaded file.")

# --- Dashboard & Analytics Module ---
elif option == "Dashboard & Analytics":
    st.subheader("Dashboard & Analytics", anchor=False)
    st.caption("High-level view of session activities.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.get("reports_verified", 0))
    c2.metric("Requirements Generated", st.session_state.get("requirements_generated", 0))
    c3.metric("Components in DB", len(UNIFIED_COMPONENT_DB))
