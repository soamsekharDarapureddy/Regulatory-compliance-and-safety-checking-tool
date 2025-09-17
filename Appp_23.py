# app.py
import streamlit as st
import pandas as pd
import pdfplumber
import openpyxl
import re
import os

# To parse .docx files, you need to install python-docx
try:
    import docx
except ImportError:
    st.error("The 'python-docx' library is not installed. Please install it by running: pip install python-docx")
    st.stop()

# === Branding & Page Config ===
st.set_page_config(page_title="Regulatory Compliance & Safety Tool", layout="wide")

# --- FINAL, CORRECTED LOGO AND TITLE LAYOUT ---
col1, col2 = st.columns([1, 4])  # Create two columns, the second being wider

with col1:
    # This code finds and displays the logo in the first (left) column.
    def find_logo_path(possible_names=["logo.jpg", "logo.png", "logo.png.jpg"]):
        for name in possible_names:
            if os.path.exists(name):
                return name
        return None

    logo_path = find_logo_path()
    if logo_path:
        try:
            st.image(logo_path, width=150)
        except Exception as e:
            st.error(f"Error loading logo: {e}")
    else:
        st.warning("Logo not found.")

with col2:
    # This code displays the title in the second (right) column.
    st.title("Regulatory Compliance & Safety Verification Tool")


# === Advanced CSS for Styling ===
st.markdown("""
<style>
.card{background:#f9f9f9; border-radius:10px; padding:15px; margin-bottom:10px; border-left: 5px solid #0056b3;}
.small-muted{color:#777; font-size:0.95em;}
.result-pass{color:#1e9f50; font-weight:700;}
.result-fail{color:#c43a31; font-weight:700;}
.main .block-container { padding-top: 2rem; }
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


# === UPGRADED KNOWLEDGE BASE with Detailed Procedures ===
TEST_CASE_KNOWLEDGE_BASE = {
    "water ingress": {
        "name": "Water Ingress Protection Test (IPX7)",
        "standard": "Based on ISO 20653 / IEC 60529",
        "description": "This test simulates the temporary immersion of the device in water to ensure no harmful quantity of water can enter the enclosure.",
        "procedure": [
            "Ensure the Device Under Test (DUT) is in a non-operational state and at ambient temperature.",
            "Submerge the DUT completely in a water tank.",
            "The lowest point of the DUT should be 1 meter below the surface of the water.",
            "The highest point of the DUT should be at least 0.15 meters below the surface.",
            "Maintain the immersion for the specified duration.",
            "After the test, remove the DUT, dry the exterior, and inspect the interior for any signs of water ingress.",
            "Conduct a functional check to ensure the device operates as expected."
        ],
        "parameters": {
            "Immersion Depth": "1 meter",
            "Test Duration": "30 minutes",
            "Water Temperature": "Ambient (within 5°C of DUT temperature)"
        },
        "equipment": ["Water Immersion Tank", "Depth Measurement Tool", "Stopwatch"]
    },
    "thermal shock": {
        "name": "Thermal Shock Test",
        "standard": "Based on ISO 16750-4",
        "description": "This test simulates the stress placed on electronic components when moving between extreme temperatures, such as a car being washed in winter.",
        "procedure": [
            "Set up a dual-chamber thermal shock system (hot and cold chambers).",
            "Place the DUT in the cold chamber and allow it to stabilize at the minimum temperature.",
            "Rapidly transfer the DUT to the hot chamber (transfer time should be less than 1 minute).",
            "Allow the DUT to stabilize at the maximum temperature.",
            "This completes one cycle. Repeat for the specified number of cycles.",
            "After the final cycle, allow the DUT to return to room temperature and perform a full functional and visual inspection."
        ],
        "parameters": {
            "Minimum Temperature": "-40°C",
            "Maximum Temperature": "+85°C",
            "Soak Time per Chamber": "1 hour",
            "Number of Cycles": "100 cycles"
        },
        "equipment": ["Dual-Chamber Thermal Shock System"]
    },
    "vibration": {
        "name": "Sinusoidal Vibration Test",
        "standard": "Based on IEC 60068-2-6",
        "description": "This test simulates the vibrations that a component might experience during its operational life due to engine harmonics or rough road conditions.",
        "procedure": [
            "Securely mount the DUT onto the vibration shaker table in its intended orientation.",
            "Sweep the frequency range from the minimum to the maximum value and back down.",
            "Perform the sweep on all three axes (X, Y, and Z).",
            "Maintain the specified G-force (acceleration) throughout the test.",
            "During the test, monitor the DUT for any intermittent failures or resonant frequencies.",
            "After the test, perform a full functional and visual inspection for any damage."
        ],
        "parameters": {
            "Frequency Range": "10 Hz to 500 Hz",
            "Acceleration": "5g (49 m/s²)",
            "Sweep Rate": "1 octave/minute",
            "Duration per Axis": "2 hours"
        },
        "equipment": ["Electrodynamic Shaker Table", "Vibration Controller", "Accelerometers"]
    },
     "short circuit": {
        "name": "External Short Circuit Protection",
        "standard": "Based on AIS-156 / IEC 62133-2",
        "description": "Verifies the safety performance of the battery or system when an external short circuit is applied.",
        "procedure": [
            "Ensure the DUT is fully charged.",
            "Connect the positive and negative terminals of the DUT with a copper wire or load with a resistance of less than 100 mΩ.",
            "Maintain the short circuit condition for the specified duration or until the protection circuit interrupts the current.",
            "Monitor the DUT for any hazardous events like fire, explosion, or casing rupture.",
            "Measure the case temperature during the test; it should not exceed the specified limit.",
            "After the test, the DUT should not show signs of fire or explosion."
        ],
        "parameters": {
            "Short Circuit Resistance": "< 100 mΩ",
            "Test Temperature": "55°C ± 5°C",
            "Observation Period": "1 hour after the event"
        },
        "equipment": ["High-Current Contactor", "Low-Resistance Load", "Thermocouples", "Safety Enclosure"]
    }
}

# --- COMPLETE, UNIFIED, and FULLY POPULATED Component Database ---
UNIFIED_COMPONENT_DB = {
    "cga3e1x7r1e105k080ac": {"Manufacturer":"TDK", "Product Category":"Multilayer Ceramic Capacitors MLCC - SMD/SMT", "RoHS":"Yes", "Capacitance":"1 uF", "Voltage Rating DC":"25 VDC", "Dielectric":"X7R", "Tolerance":"10 %", "Case Code - in":"0603", "Case Code - mm":"1608", "Termination Style":"SMD/SMT", "Termination":"Standard", "Minimum Operating Temperature":"-55 C", "Maximum Operating Temperature":"+125 C", "Length":"1.6 mm", "Width":"0.8 mm", "Height":"0.8 mm", "Product":"Automotive MLCCs", "Qualification":"AEC-Q200"},
    "spc560p50l3": {"Manufacturer": "STMicroelectronics", "Product Category": "MCU", "RoHS": "Yes", "CPU Core": "PowerPC e200z0h", "Frequency": "64 MHz", "RAM Size": "48KB", "Flash Size": "512KB", "Package": "LQFP-100", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q100"},
    "tja1051t": {"Manufacturer": "NXP", "Product Category": "CAN Transceiver", "RoHS": "Yes", "Data Rate": "1 Mbps", "Voltage Rating DC": "5V", "Package": "SO-8", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q100"},
    "tle4275g": {"Manufacturer": "Infineon", "Product Category": "LDO Regulator", "RoHS": "Yes", "Output Voltage": "5V", "Output Current": "450mA", "Package": "TO-252-3", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "150 C", "Qualification": "AEC-Q100"},
    "fsbb30ch60f": {"Manufacturer": "onsemi", "Product Category": "IGBT Module", "RoHS": "Yes", "Voltage Rating DC": "600V", "Current": "30A", "Package": "SPM27-CC", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "150 C", "Product": "Smart Power Module"},
    "wslp2512r0100fe": {"Manufacturer": "Vishay", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "10 mOhm", "Power": "1W", "Tolerance": "1%", "Case Code - in": "2512", "Minimum Operating Temperature": "-65 C", "Maximum Operating Temperature": "170 C", "Qualification": "AEC-Q200"},
    "bq76952": {"Manufacturer": "Texas Instruments", "Product Category": "Battery Monitor", "RoHS": "Yes", "Cell Count": "3-16", "Interface": "I2C, SPI", "Package": "TQFP-48", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "85 C", "Qualification": "AEC-Q100"},
    "irfz44n": {"Manufacturer": "Infineon", "Product Category": "MOSFET", "RoHS": "Yes", "Vds": "55V", "Id": "49A", "Rds(on)": "17.5 mOhm", "Package": "TO-220AB", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "175 C"},
    "1n4007": {"Manufacturer": "Multiple", "Product Category": "Diode", "RoHS": "Yes", "VRRM": "1000V", "If(AV)": "1A", "Package": "DO-41", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "150 C"},
    "fh28-10s-0.5sh(05)": {"Manufacturer": "Hirose", "Product Category": "Connector", "RoHS": "Yes", "Pitch": "0.5mm", "Positions": "10", "Current": "0.5A", "Package": "FFC/FPC", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "105 C"},
    "gcm155l81e104ke02d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "0.1uF", "Voltage Rating DC": "25V", "Dielectric": "X8L", "Case Code - mm": "1005", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "150 C", "Qualification": "AEC-Q200"},
    "grt1555c1e220ja02j": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "22pF", "Voltage Rating DC": "25V", "Dielectric": "C0G", "Case Code - mm": "1005", "Tolerance": "5%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "grt155r61a475me13d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "4.7uF", "Voltage Rating DC": "10V", "Dielectric": "X5R", "Case Code - mm": "1005", "Tolerance": "20%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "85 C", "Qualification": "AEC-Q200"},
    "grt31cr61a476ke13l": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "47uF", "Voltage Rating DC": "10V", "Dielectric": "X5R", "Case Code - mm": "3216", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "85 C", "Qualification": "AEC-Q200"},
    "cga2b2c0g1h180j050ba": {"Manufacturer": "TDK", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "18pF", "Voltage Rating DC": "50V", "Dielectric": "C0G", "Case Code - mm": "1005", "Tolerance": "5%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "c0402c103k4racauto": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "10nF", "Voltage Rating DC": "16V", "Dielectric": "X7R", "Case Code - mm": "1005", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "gcm1555c1h101ja16d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "100pF", "Voltage Rating DC": "50V", "Dielectric": "C0G", "Case Code - mm": "1005", "Tolerance": "5%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "grt155r71h104ke01d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "0.1uF", "Voltage Rating DC": "50V", "Dielectric": "X7R", "Case Code - mm": "1005", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "grt21br61e226me13l": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "22uF", "Voltage Rating DC": "25V", "Dielectric": "X5R", "Case Code - mm": "2012", "Tolerance": "20%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "85 C", "Qualification": "AEC-Q200"},
    "grt1555c1h150fa02d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "15pF", "Voltage Rating DC": "50V", "Dielectric": "C0G", "Case Code - mm": "1005", "Tolerance": "1%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "0402yc222j4t2a": {"Manufacturer": "AVX", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "2.2nF", "Voltage Rating DC": "16V", "Dielectric": "X7R", "Case Code - in": "0402", "Tolerance": "5%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "gcm1555c1h560fa16d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "56pF", "Voltage Rating DC": "50V", "Dielectric": "C0G", "Case Code - mm": "1005", "Tolerance": "1%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "grt1555c1h330fa02d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "33pF", "Voltage Rating DC": "50V", "Dielectric": "C0G", "Case Code - mm": "1005", "Tolerance": "1%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "grt188c81a106me13d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "10uF", "Voltage Rating DC": "10V", "Dielectric": "X6S", "Case Code - mm": "1608", "Tolerance": "20%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "105 C", "Qualification": "AEC-Q200"},
    "umk212b7105kfna01": {"Manufacturer": "Taiyo Yuden", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "1uF", "Voltage Rating DC": "50V", "Dielectric": "X7R", "Case Code - in": "0805", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C"},
    "c1206c104k5racauto": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "0.1uF", "Voltage Rating DC": "50V", "Dielectric": "X7R", "Case Code - in": "1206", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "grt31cr61h106ke01k": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "10uF", "Voltage Rating DC": "50V", "Dielectric": "X5R", "Case Code - in": "1206", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "85 C", "Qualification": "AEC-Q200"},
    "c0402c333k4racauto": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "33nF", "Voltage Rating DC": "16V", "Dielectric": "X7R", "Case Code - in": "0402", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "cl10b474ko8vpnc": {"Manufacturer": "Samsung", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "0.47uF", "Voltage Rating DC": "16V", "Dielectric": "X7R", "Case Code - in": "0603", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C"},
    "gcm155r71c224ke02d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "0.22uF", "Voltage Rating DC": "16V", "Dielectric": "X7R", "Case Code - mm": "1005", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "gcm155r71h102ka37j": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "1nF", "Voltage Rating DC": "50V", "Dielectric": "X7R", "Case Code - mm": "1005", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "50tpv330m10x10.5": {"Manufacturer": "Panasonic", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "330uF", "Voltage Rating DC": "50V", "Type": "Polymer", "ESR": "18 mOhm", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "105 C"},
    "cl31b684kbhwpne": {"Manufacturer": "Samsung", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "0.68uF", "Voltage Rating DC": "50V", "Dielectric": "X7R", "Case Code - in": "1206", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C"},
    "gcm155r71h272ka37d": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "2.7nF", "Voltage Rating DC": "50V", "Dielectric": "X7R", "Case Code - mm": "1005", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "edk476m050s9haa": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "47uF", "Voltage Rating DC": "50V", "Type": "Aluminum Electrolytic", "ESR": "700 mOhm", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "105 C"},
    "gcm155r71h332ka37j": {"Manufacturer": "Murata", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "3.3nF", "Voltage Rating DC": "50V", "Dielectric": "X7R", "Case Code - mm": "1005", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "a768ke336m1hlae042": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "33uF", "Voltage Rating DC": "50V", "Type": "Polymer", "ESR": "42 mOhm", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "ac0402jrx7r9bb152": {"Manufacturer": "Yageo", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "1.5nF", "Voltage Rating DC": "50V", "Dielectric": "X7R", "Case Code - in": "0402", "Tolerance": "5%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "d5v0h1b2lpq-7b": {"Manufacturer": "Diodes Inc.", "Product Category": "TVS Diode", "RoHS": "Yes", "V Rwm": "5V", "Power": "30W", "Package": "X2-DFN1006-2", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "150 C"},
    "szmmbz9v1alt3g": {"Manufacturer": "onsemi", "Product Category": "Zener Diode", "RoHS": "Yes", "Vz": "9.1V", "Power": "225mW", "Tolerance": "5%", "Package": "SOT-23", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "150 C"},
    "d24v0s1u2tq-7": {"Manufacturer": "Diodes Inc.", "Product Category": "TVS Diode Array", "RoHS": "Yes", "V Rwm": "24V", "Channels": "1", "Package": "SOD-323", "Minimum Operating Temperature": "-65 C", "Maximum Operating Temperature": "150 C"},
    "b340bq-13-f": {"Manufacturer": "Diodes Inc.", "Product Category": "Schottky Diode", "RoHS": "Yes", "VRRM": "40V", "If(AV)": "3A", "Package": "SMC", "Minimum Operating Temperature": "-65 C", "Maximum Operating Temperature": "150 C", "Qualification": "AEC-Q101"},
    "tld8s22ah": {"Manufacturer": "Infineon", "Product Category": "TVS Diode", "RoHS": "Yes", "V Rwm": "22V", "Power": "8000W", "Package": "DO-218AB", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "175 C", "Qualification": "AEC-Q101"},
    "b260aq-13-f": {"Manufacturer": "Diodes Inc.", "Product Category": "Schottky Diode", "RoHS": "Yes", "VRRM": "60V", "If(AV)": "2A", "Package": "SMB", "Minimum Operating Temperature": "-65 C", "Maximum Operating Temperature": "150 C", "Qualification": "AEC-Q101"},
    "rb530sm-40fht2r": {"Manufacturer": "ROHM", "Product Category": "Schottky Diode", "RoHS": "Yes", "VRM": "40V", "IF": "30mA", "Package": "SOD-523", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C"},
    "74279262": {"Manufacturer": "Würth Elektronik", "Product Category": "Ferrite Bead", "RoHS": "Yes", "Impedance @ 100MHz": "220 Ohm", "Current": "3A", "Package": "0805", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "742792641": {"Manufacturer": "Würth Elektronik", "Product Category": "Ferrite Bead", "RoHS": "Yes", "Impedance @ 100MHz": "1000 Ohm", "Current": "1.5A", "Package": "0805", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "742792625": {"Manufacturer": "Würth Elektronik", "Product Category": "Ferrite Bead", "RoHS": "Yes", "Impedance @ 100MHz": "500 Ohm", "Current": "2.5A", "Package": "0805", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "742792150": {"Manufacturer": "Würth Elektronik", "Product Category": "Ferrite Bead", "RoHS": "Yes", "Impedance @ 100MHz": "30 Ohm", "Current": "6A", "Package": "1206", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "voma617a-4x001t": {"Manufacturer": "Vishay", "Product Category": "Optocoupler", "RoHS": "Yes", "Type": "Transistor Output", "CTR": "100-200%", "Package": "SOP-4", "Isolation": "3750Vrms", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "110 C", "Qualification": "AEC-Q101"},
    "534260610": {"Manufacturer": "Molex", "Product Category": "Connector", "RoHS": "Yes", "Type": "Pico-Lock", "Positions": "6", "Pitch": "1.5mm", "Termination Style": "Wire-to-Board Header", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "105 C"},
    "fh52-40s-0.5sh(99)": {"Manufacturer": "Hirose", "Product Category": "Connector", "RoHS": "Yes", "Pitch": "0.5mm", "Positions": "40", "Current": "0.5A", "Termination Style": "FFC/FPC", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "105 C"},
    "744235510": {"Manufacturer": "Würth Elektronik", "Product Category": "Inductor", "RoHS": "Yes", "Inductance": "51uH", "Current": "1.8A", "Package": "Shielded SMD", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "lqw15an56nj8zd": {"Manufacturer": "Murata", "Product Category": "Inductor", "RoHS": "Yes", "Inductance": "56nH", "Current": "350mA", "Case Code - in": "0402", "Tolerance": "5%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "spm7054vt-220m-d": {"Manufacturer": "Sumida", "Product Category": "Inductor", "RoHS": "Yes", "Inductance": "22uH", "Current": "3.1A", "Package": "7mm SMD", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C"},
    "744273801": {"Manufacturer": "Würth Elektronik", "Product Category": "Inductor", "RoHS": "Yes", "Inductance": "8uH", "Current": "1.8A", "Package": "Shielded SMD", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "74404084068": {"Manufacturer": "Würth Elektronik", "Product Category": "Inductor", "RoHS": "Yes", "Inductance": "6.8uH", "Current": "2.2A", "Package": "0804", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "125 C"},
    "744231091": {"Manufacturer": "Würth Elektronik", "Product Category": "Inductor", "RoHS": "Yes", "Inductance": "0.9uH", "Current": "6.5A", "Package": "Shielded SMD", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "150 C", "Qualification": "AEC-Q200"},
    "mlz2012m6r8htd25": {"Manufacturer": "TDK", "Product Category": "Inductor", "RoHS": "Yes", "Inductance": "6.8uH", "Current": "300mA", "Case Code - in": "0805", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
    "rq3g270bjfratcb": {"Manufacturer": "ROHM", "Product Category": "MOSFET", "RoHS": "Yes", "Vds": "20V", "Id": "27A", "Rds(on)": "2.8 mOhm", "Package": "HSMT8", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "150 C"},
    "pja138k-au_r1_000a1": {"Manufacturer": "PANJIT", "Product Category": "MOSFET", "RoHS": "Yes", "Vds": "100V", "Id": "7A", "Rds(on)": "138 mOhm", "Package": "SOT-223", "Qualification": "AEC-Q101"},
    "dmp2070uq-7": {"Manufacturer": "Diodes Inc.", "Product Category": "MOSFET", "RoHS": "Yes", "Vds": "20V", "Id": "5.6A", "Rds(on)": "38 mOhm", "Package": "SOT-23", "Qualification": "AEC-Q101"},
    "ac0402jr-070rl": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "0 Ohm", "Power": "0.063W", "Case Code - in": "0402", "Product": "Jumper", "Qualification": "AEC-Q200"},
    "ac0402fr-07100kl": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "100 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft158k": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "158 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft30k0": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "30 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft127k": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "127 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmc10k204fth": {"Manufacturer": "Kamaya", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "200 kOhm", "Power": "0.125W", "Tolerance": "1%", "Case Code - in": "0805", "Qualification": "AEC-Q200"},
    "erj-2rkf2201x": {"Manufacturer": "Panasonic", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "2.2 kOhm", "Power": "0.1W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "erj-2rkf1002x": {"Manufacturer": "Panasonic", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "10 kOhm", "Power": "0.1W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "wr04x1004ftl": {"Manufacturer": "Walsin", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "1 MOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "wr04x10r0ftl": {"Manufacturer": "Walsin", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "10 Ohm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rc0603fr-0759rl": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "59 Ohm", "Power": "0.1W", "Tolerance": "1%", "Case Code - in": "0603", "Qualification": "AEC-Q200"},
    "ac0402fr-07100rl": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "100 Ohm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "ac0402fr-076k04l": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "6.04 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "ac0402fr-07510rl": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "510 Ohm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "crgcq0402f56k": {"Manufacturer": "TE Connectivity", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "56 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft24k9": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "24.9 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft5k36": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "5.36 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0603ft12k0": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "12 kOhm", "Power": "0.1W", "Tolerance": "1%", "Case Code - in": "0603", "Qualification": "AEC-Q200"},
    "rmcf0402ft210k": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "210 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "ltr18ezpfsr015": {"Manufacturer": "ROHM", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "15 mOhm", "Power": "1.5W", "Tolerance": "1%", "Case Code - in": "1206", "Qualification": "AEC-Q200"},
    "erj-pa2j102x": {"Manufacturer": "Panasonic", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "1 kOhm", "Power": "0.25W", "Tolerance": "5%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft5k10": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "5.1 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0603ft100r": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "100 Ohm", "Power": "0.1W", "Tolerance": "1%", "Case Code - in": "0603", "Qualification": "AEC-Q200"},
    "ac0402jr-074k7l": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "4.7 kOhm", "Power": "0.063W", "Tolerance": "5%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "crf0805-fz-r010elf": {"Manufacturer": "Bourns", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "10 mOhm", "Power": "0.5W", "Tolerance": "1%", "Case Code - in": "0805", "Qualification": "AEC-Q200"},
    "rmcf0402ft3k16": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "3.16 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft3k48": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "3.48 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft1k50": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "1.5 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf0402ft4k02": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "4.02 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "rmcf1206zt0r00": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "0 Ohm", "Power": "0.25W", "Case Code - in": "1206", "Product": "Jumper", "Qualification": "AEC-Q200"},
    "rmcf0402ft402k": {"Manufacturer": "Stackpole", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "402 kOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
    "ac0603fr-7w20kl": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "20 kOhm", "Power": "0.1W", "Tolerance": "1%", "Case Code - in": "0603", "Qualification": "AEC-Q200"},
    "h164yp": {"Manufacturer": "Yageo", "Product Category": "Resistor Array", "RoHS": "Yes", "Resistance": "10 kOhm", "Elements": "4", "Package": "0804", "Tolerance": "5%"},
    "zldo1117qg33ta": {"Manufacturer": "Diodes Inc.", "Product Category": "LDO Regulator", "RoHS": "Yes", "Output Voltage": "3.3V", "Output Current": "1A", "Package": "SOT-223", "Qualification": "AEC-Q100"},
    "ap63357qzv-7": {"Manufacturer": "Diodes Inc.", "Product Category": "Buck Converter", "RoHS": "Yes", "Input Voltage": "3.8V-32V", "Output Current": "3.5A", "Package": "SOT-563", "Qualification": "AEC-Q100"},
    "pca9306idcurq1": {"Manufacturer": "Texas Instruments", "Product Category": "I2C Translator", "RoHS": "Yes", "Channels": "2", "Voltage Range": "1V-5.5V", "Package": "VSSOP-8", "Qualification": "AEC-Q100"},
    "mcp2518fdt-e/sl": {"Manufacturer": "Microchip", "Product Category": "CAN FD Controller", "RoHS": "Yes", "Data Rate": "8 Mbps", "Interface": "SPI", "Package": "SOIC-14", "Qualification": "AEC-Q100"},
    "iso1042bqdwvq1": {"Manufacturer": "Texas Instruments", "Product Category": "CAN Transceiver", "RoHS": "Yes", "Product": "Isolated", "Data Rate": "5 Mbps", "Package": "SOIC-16", "Qualification": "AEC-Q100"},
    "pesd2canfd27v-tr": {"Manufacturer": "Nexperia", "Product Category": "ESD Suppressor", "RoHS": "Yes", "Bus Type": "CAN", "V Rwm": "27V", "Package": "SOT-23", "Qualification": "AEC-Q101"},
    "lt8912b": {"Manufacturer": "Analog Devices", "Product Category": "MIPI DSI to LVDS Bridge", "RoHS": "Yes", "Lanes": "4", "Resolution": "1080p", "Package": "QFN-48"},
    "sn74lv1t34qdckrq1": {"Manufacturer": "Texas Instruments", "Product Category": "Buffer Gate", "RoHS": "Yes", "Channels": "1", "Direction": "Uni-Directional", "Package": "SC-70", "Qualification": "AEC-Q100"},
    "ncp164csnadjt1g": {"Manufacturer": "onsemi", "Product Category": "LDO Regulator", "RoHS": "Yes", "Output Voltage": "Adj", "Output Current": "250mA", "Package": "TSOP-5", "Qualification": "AEC-Q100"},
    "20279-001e-03": {"Manufacturer": "Amphenol", "Product Category": "Antenna", "RoHS": "Yes", "Product": "GPS", "Gain": "28 dBi", "Termination Style": "Adhesive"},
    "ncv8161asn180t1g": {"Manufacturer": "onsemi", "Product Category": "LDO Regulator", "RoHS": "Yes", "Output Voltage": "1.8V", "Output Current": "450mA", "Package": "TSOP-5", "Qualification": "AEC-Q100"},
    "drtr5v0u2sr-7": {"Manufacturer": "Diodes Inc.", "Product Category": "ESD Suppressor", "RoHS": "Yes", "V Rwm": "5V", "Channels": "2", "Package": "SOT-23", "Qualification": "AEC-Q101"},
    "ncv8161asn330t1g": {"Manufacturer": "onsemi", "Product Category": "LDO Regulator", "RoHS": "Yes", "Output Voltage": "3.3V", "Output Current": "450mA", "Package": "TSOP-5", "Qualification": "AEC-Q100"},
    "ecmf04-4hswm10y": {"Manufacturer": "STMicroelectronics", "Product Category": "ESD Filter", "RoHS": "Yes", "Channels": "4", "Bus Type": "HDMI", "Package": "WLCSP-10", "Qualification": "AEC-Q101"},
    "nxs0102dc-q100h": {"Manufacturer": "Nexperia", "Product Category": "Level Translator", "RoHS": "Yes", "Channels": "2", "Direction": "Bi-Directional", "Package": "VSSOP-8", "Qualification": "AEC-Q100"},
    "cf0505xt-1wr3": {"Manufacturer": "Mornsun", "Product Category": "DC/DC Converter", "RoHS": "Yes", "Power": "1W", "Input Voltage": "4.5V-5.5V", "Output Voltage": "5V", "Isolation": "3kVDC", "Package": "SIP"},
    "iam-20680ht": {"Manufacturer": "TDK InvenSense", "Product Category": "IMU", "RoHS": "Yes", "Axes": "6", "Interface": "SPI, I2C", "Package": "LGA-16", "Qualification": "AEC-Q100"},
    "attiny1616-szt-vao": {"Manufacturer": "Microchip", "Product Category": "MCU", "RoHS": "Yes", "CPU Core": "AVR", "Frequency": "20MHz", "RAM Size": "2KB", "Flash Size": "16KB", "Package": "SOIC-24", "Qualification": "AEC-Q100"},
    "tlv9001qdckrq1": {"Manufacturer": "Texas Instruments", "Product Category": "Op-Amp", "RoHS": "Yes", "Channels": "1", "GBW": "1MHz", "Package": "SC-70", "Qualification": "AEC-Q100"},
    "qmc5883l": {"Manufacturer": "QST", "Product Category": "Magnetometer", "RoHS": "Yes", "Axes": "3", "Interface": "I2C", "Package": "LGA-12"},
    "lm76202qpwprq1": {"Manufacturer": "Texas Instruments", "Product Category": "Ideal Diode Controller", "RoHS": "Yes", "Input Voltage": "3V-60V", "Package": "HTSSOP-16", "Qualification": "AEC-Q100"},
    "bd83a04efv-me2": {"Manufacturer": "ROHM", "Product Category": "DC/DC Converter", "RoHS": "Yes", "Type": "Buck", "Input Voltage": "4.5V-40V", "Output Current": "4A", "Package": "HTSOP-J8", "Qualification": "AEC-Q100"},
    "ecs-200-12-33q-jes-tr": {"Manufacturer": "ECS Inc.", "Product Category": "Crystal", "RoHS": "Yes", "Frequency": "20MHz", "Tolerance": "10ppm", "Package": "3.2x2.5mm", "Qualification": "AEC-Q200"},
    "ecs-250-12-33q-jes-tr": {"Manufacturer": "ECS Inc.", "Product Category": "Crystal", "RoHS": "Yes", "Frequency": "25MHz", "Tolerance": "10ppm", "Package": "3.2x2.5mm", "Qualification": "AEC-Q200"},
    "aggbp.25a.07.0060a": {"Manufacturer": "Taoglas", "Product Category": "Antenna", "RoHS": "Yes", "Product": "GPS Patch", "Frequency": "1575.42MHz", "Package": "25x25mm"},
    "y4ete00a0aa": {"Manufacturer": "Quectel", "Product Category": "LTE Module", "RoHS": "Yes", "Series": "EC25-AFX", "Bands": "LTE-FDD, T-Mobile, AT&T", "Package": "LCC"},
    "yf0023aa": {"Manufacturer": "Quectel", "Product Category": "LTE Antenna", "RoHS": "Yes", "Frequency Range": "698-2690MHz", "Cable": "RG178", "Termination": "MHF-I"},
    "mb9df125": {"Manufacturer": "Cypress/Infineon", "Product Category": "MCU", "RoHS": "Yes", "CPU Core": "ARM Cortex-R4", "Frequency": "128MHz", "RAM Size": "96KB", "Flash Size": "1MB", "Package": "LQFP-208"},
    "veml6031x00": {"Manufacturer": "Vishay", "Product Category": "Light Sensor", "RoHS": "Yes", "Product": "Ambient Light", "Interface": "I2C", "Package": "2x2mm OPLGA", "Qualification": "AEC-Q100"},
    "01270019-00": {"Manufacturer": "Custom", "Product Category": "Cable Assembly", "Description": "Main harness wiring"},
    "01270020-00": {"Manufacturer": "Custom", "Product Category": "Cable Assembly", "Description": "Display interface cable"},
    "01270021-00": {"Manufacturer": "Custom", "Product Category": "Cable Assembly", "Description": "I/O port wiring"},
    "p0024-03": {"Manufacturer": "Custom", "Product Category": "PCB", "Description": "Main Logic Board"},
    "01270018-00": {"Manufacturer": "Custom", "Product Category": "Enclosure", "Description": "Main device housing"},
    "01270010-02": {"Manufacturer": "Custom", "Product Category": "Accessory", "Description": "Mounting bracket kit"}
}

def intelligent_parser(text: str):
    extracted_tests = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line: continue
        
        test_data = {"TestName": "Not found", "Result": "N/A", "Actual": "Not found", "Standard": "Not found"}
        
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
                if i == 0: test_data.update({"TestName": groups[0].strip(), "Result": "PASS" if groups[1].lower() in ["passed", "success"] else "FAIL", "Actual": groups[2].strip()})
                elif i == 1:
                    result_str = groups[1].lower()
                    result = "PASS" if "passed" in result_str or "success" in result_str else "FAIL" if "failed" in result_str else "INFO"
                    test_data.update({"TestName": groups[0].strip(), "Result": result, "Actual": groups[1].strip()})
                elif i == 2: test_data.update({"TestName": groups[0].replace("_", " ").strip(), "Result": groups[1].upper()})
                elif i == 3: test_data.update({"TestName": groups[0].strip(), "Result": "PASS" if groups[1].lower() in ["success", "passed"] else "FAIL"})
                elif i == 4: test_data.update({"TestName": groups[0].strip(), "Result": "PASS" if groups[1].lower() == "passed" else "FAIL"})
                match_found = True
                break
        
        if match_found:
            KEYWORD_TO_STANDARD_MAP = {
                "gps": "NMEA 0183", "gnss": "3GPP", "bluetooth": "Bluetooth Core Specification", "wifi": "IEEE 802.11",
                "lte": "3GPP LTE", "can": "ISO 11898", "sensor": "AEC-Q104", "ip rating": "IEC 60529",
                "short circuit": "AIS-156 / IEC 62133", "overcharge": "AIS-156", "vibration": "IEC 60068-2-6"
            }
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
option = st.sidebar.radio("Navigate", ("Component Information", "Test Requirement Generation", "Test Report Verification", "Dashboard & Analytics"))
st.sidebar.info("An integrated tool for automotive compliance.")

# --- Component Information Module (with swapped columns) ---
if option == "Component Information":
    st.subheader("Key Component Information", anchor=False)
    st.caption("Look up parts from the fully populated component database.")
    
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., gcm155l81e104ke02d").lower().strip()
    
    if st.button("Find Component"):
        if part_q:
            db_for_search = {k.lower(): v for k, v in UNIFIED_COMPONENT_DB.items()}
            result = db_for_search.get(part_q)

            if result:
                st.session_state.found_component = result
                st.session_state.searched_part = part_q
                st.success(f"Found: {part_q.upper()}. Displaying details below.")
            else:
                st.session_state.found_component = None
                st.warning("Part number not found in the database.")
    
    if st.session_state.get('found_component'):
        st.markdown("---")
        component = st.session_state.found_component
        st.markdown(f"### Details for: {st.session_state.searched_part.upper()}")

        if st.session_state.searched_part == 'gcm155l81e104ke02d':
            component.setdefault('Part Name', '0.1µF 25V X8L 0402 Capacitor')
            component.setdefault('Use', 'General Purpose Decoupling')
            component.setdefault('Category', 'Capacitors')
            component.setdefault('Type', 'Ceramic')
            component.setdefault('Package Case', '0402')
            component.setdefault('Operating Temp Range', '-55°C to 150°C')

        fields_order = [
            "Part Number", "Part Name", "Manufacturer", "Use", "Category", "Type",
            "Capacitance", "Voltage Rating DC", "Tolerance", "Dielectric", "Package Case", "Operating Temp Range"
        ]

        display_data = {field: component.get(field, "") for field in fields_order}
        display_data['Part Number'] = st.session_state.searched_part

        data_items = list(display_data.items())
        
        col1, col2 = st.columns(2)
        midpoint = (len(data_items) + 1) // 2
        
        with col1:
            for key, value in data_items[midpoint:]:
                st.markdown(f"**{key}**")
                st.markdown(str(value) if str(value).strip() else " ")
                st.markdown("---")

        with col2:
            for key, value in data_items[:midpoint]:
                st.markdown(f"**{key}**")
                st.markdown(str(value) if str(value).strip() else " ")
                st.markdown("---")

# --- CORRECTED Test Requirement Generation Module ---
elif option == "Test Requirement Generation":
    st.subheader("Generate Detailed Test Requirements", anchor=False)
    st.caption("Enter keywords (e.g., 'water', 'vibration') to generate detailed automotive test procedures.")
    
    available_tests = list(TEST_CASE_KNOWLEDGE_BASE.keys())
    
    text_input = st.text_input("Enter a test case keyword", placeholder=f"Try: {', '.join(available_tests)}")

    if st.button("Generate Requirements"):
        user_case = text_input.strip().lower()
        if user_case:
            st.session_state.requirements_generated += 1
            
            matched_test = None
            for key, test_data in TEST_CASE_KNOWLEDGE_BASE.items():
                if user_case in key:
                    matched_test = test_data
                    break
            
            if matched_test:
                st.markdown(f"#### Generated Procedure for: **{matched_test.get('name', 'N/A')}**")
                
                # Using a styled container for the output
                with st.container():
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    
                    st.markdown(f"**Standard:** {matched_test.get('standard', 'N/A')}")
                    st.markdown(f"**Description:** {matched_test.get('description', 'N/A')}")
                    
                    st.markdown("**Test Procedure:**")
                    for step in matched_test.get('procedure', []):
                        st.markdown(f"- {step}")

                    st.markdown("**Key Parameters:**")
                    for param, value in matched_test.get('parameters', {}).items():
                        st.markdown(f"- **{param}:** {value}")

                    st.markdown(f"**Required Equipment:** {', '.join(matched_test.get('equipment', ['N/A']))}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning(f"No detailed procedure found for '{user_case}'. Please try one of the following keywords: {', '.join(available_tests)}")


# --- Test Report Verification Module ---
elif option == "Test Report Verification":
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


# --- Dashboard & Analytics Module ---
elif option == "Dashboard & Analytics":
    st.subheader("Dashboard & Analytics", anchor=False)
    st.caption("High-level view of session activities.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.reports_verified)
    c2.metric("Requirements Generated", st.session_state.requirements_generated)
    c3.metric("Components in DB", len(UNIFIED_COMPONENT_DB))
