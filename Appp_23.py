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
col1, col2 = st.columns([1, 4])

with col1:
    # This function looks for 'logo.png' (or other formats) in the local directory.
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
    # Title with "Royal" color for an impressive look
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
        "reports_verified": 0, "requirements_generated": 0, "found_component": None,
        "component_db": pd.DataFrame()
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()

# === FULLY RESTORED KNOWLEDGE BASE WITH DEEPER INFO & IMAGES ===
TEST_CASE_KNOWLEDGE_BASE = {
    "water ingress": {
        "name": "Water Ingress Protection Test (IPX7)", "standard": "Based on ISO 20653 / IEC 60529",
        "description": "This test simulates the temporary immersion of the device in water to ensure no harmful quantity of water can enter the enclosure.",
        "procedure": [
            "Ensure the Device Under Test (DUT) is in a non-operational state and at ambient temperature.",
            "Submerge the DUT completely in a water tank.",
            "The lowest point of the DUT should be 1 meter below the surface of the water.",
            "The highest point of the DUT should be at least 0.15 meters below the surface.",
            "Maintain the immersion for 30 minutes.",
            "After the test, remove the DUT, dry the exterior, and inspect the interior for any signs of water ingress.",
            "Conduct a full functional check to ensure the device operates as expected."
        ],
        "equipment": ["Water Immersion Tank", "Depth Measurement Tool", "Stopwatch", "Post-test Inspection Tools"],
        "image_url": ""
    },
    "thermal shock": {
        "name": "Thermal Shock Test", "standard": "Based on ISO 16750-4",
        "description": "Simulates the extreme stress placed on electronic components and their solder joints when moving between extreme temperatures rapidly.",
        "procedure": [
            "Set up a dual-chamber thermal shock system (hot and cold chambers).",
            "Place the DUT in the cold chamber and allow it to stabilize at the minimum temperature (e.g., -40°C).",
            "Rapidly transfer the DUT to the hot chamber (transfer time should be less than 1 minute).",
            "Allow the DUT to stabilize at the maximum temperature (e.g., +125°C).",
            "This completes one cycle. Repeat for the specified number of cycles (e.g., 100 or 1000 cycles).",
            "After the final cycle, allow the DUT to return to room temperature and perform a full functional and visual inspection for any damage."
        ],
        "equipment": ["Dual-Chamber Thermal Shock System", "Temperature Controller", "Monitoring Devices"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/43e47e6a-f0c8-41fd-b191-50c020769fcb.png"
    },
    "vibration": {
        "name": "Vibration Test", "standard": "Based on IEC 60068-2-6",
        "description": "This test simulates the vibrations that a component might experience during its operational life due to engine harmonics or rough road conditions.",
        "procedure": [
            "Securely mount the DUT onto the vibration shaker table in its intended operational orientation.",
            "Sweep the frequency range from the minimum to the maximum value and back down (e.g., 10 Hz to 500 Hz).",
            "Perform the sweep on all three axes (X, Y, and Z).",
            "Maintain the specified G-force (acceleration) throughout the test.",
            "During the test, monitor the DUT for any intermittent failures or resonant frequencies.",
            "After the test, perform a full functional and visual inspection for any damage."
        ],
        "equipment": ["Electrodynamic Shaker Table", "Vibration Controller", "Accelerometers", "Data Acquisition System"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/dbec2cd4-b4dd-410b-b79f-3e6403f51821.png"
    },
    "short circuit": {
        "name": "External Short Circuit Protection", "standard": "Based on AIS-156 / IEC 62133-2",
        "description": "Verifies the safety performance of a battery or system when an external short circuit is applied, ensuring it does not result in a hazardous event.",
        "procedure": [
            "Ensure the DUT (typically a battery pack) is fully charged.",
            "Connect the positive and negative terminals of the DUT with a copper wire or load with a resistance of less than 100 mΩ.",
            "Maintain the short circuit condition for a specified duration or until the protection circuit interrupts the current.",
            "Monitor the DUT for any hazardous events like fire, explosion, or casing rupture.",
            "Measure the case temperature during the test; it should not exceed the specified safety limit.",
            "After the test, the DUT should not show signs of fire or explosion."
        ],
        "equipment": ["High-Current Contactor", "Low-Resistance Load", "Thermocouples", "Safety Enclosure", "High-speed Camera"],
        "image_url": ""
    },
    "high temperature endurance": {
        "name": "High Temperature Endurance Test", "standard": "IEC 60068-2-2",
        "description": "Evaluates the ability of the component to withstand prolonged operation under elevated temperatures without performance degradation or failure.",
        "procedure": [
            "Place the DUT inside a calibrated thermal chamber set to the target high temperature (typically +85°C or +125°C).",
            "Operate the DUT continuously under its typical operating conditions or specified stress conditions for a predetermined duration (e.g., 1000 hours).",
            "Monitor key performance parameters such as voltage, current, and temperature at set intervals during the test.",
            "Upon completion, visually inspect the DUT for any signs of material degradation, discoloration, or mechanical failure.",
            "Perform full functional tests to verify the device operates within specifications post-test."
        ],
        "equipment": ["Thermal chamber with temperature control", "Data acquisition system for operational monitoring", "Environmental chamber accessories"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/43e47e6a-f0c8-41fd-b191-50c020769fcb.png"
    },
    "low temperature endurance": {
        "name": "Low Temperature Endurance Test", "standard": "IEC 60068-2-1",
        "description": "Assesses the component’s functional reliability and mechanical integrity under prolonged exposure to low temperature environments.",
        "procedure": [
            "Place the DUT inside the thermal chamber set at the specified low temperature (commonly -40°C or lower).",
            "Power the DUT and monitor its behavior over the specified test duration.",
            "Periodically perform operational verification such as functional checks during the exposure period.",
            "After completion of the test, inspect the DUT for physical or performance anomalies.",
            "Document all observations and performance data for evaluation."
        ],
        "equipment": ["Low temperature thermal chamber", "Functionality test benches", "Sensor data loggers"],
        "image_url": ""
    },
    "temperature cycling": {
        "name": "Temperature Cycling Test", "standard": "IEC 60068-2-14",
        "description": "Measures the robustness of components against cyclic thermal stress typically caused by on/off cycles or environmental temperature fluctuations.",
        "procedure": [
            "Mount the DUT securely inside a thermal cycling chamber.",
            "Cycle the temperature between two limits (e.g., -40°C to +125°C) using ramp rates and dwell times as defined in the test requirements.",
            "Repeat the defined number of cycles (e.g., 1000 cycles) to simulate expected service life.",
            "Monitor for any visible signs of cracking, solder joint failures, or other mechanical damage following cycles.",
            "Perform electrical functional tests before and after the cycling to detect latent failures."
        ],
        "equipment": ["Thermal cycling chamber", "Precision temperature controllers", "Mechanical inspection tools"],
        "image_url": ""
    },
    "humidity & damp heat test": {
        "name": "Humidity and Damp Heat Test", "standard": "IEC 60068-2-78",
        "description": "Tests endurance of device against moisture ingress and humidity under elevated temperature, simulating tropical and harsh environmental conditions.",
        "procedure": [
            "Place the DUT in a humidity chamber with controlled humidity (e.g., 85% RH) and temperature (e.g., +85°C).",
            "Maintain the test conditions steadily for a required length of time (e.g., 1000 hours for steady-state test).",
            "Periodically monitor the electrical parameters of the DUT and check for condensation forming on critical points.",
            "Post-exposure, visually inspect for corrosion, delamination, or material degradation.",
            "Perform comprehensive functional testing to confirm operational integrity."
        ],
        "equipment": ["Humidity chamber with precise RH and temperature control", "Electrical monitoring systems", "Moisture sensors"],
        "image_url": ""
    },
    "salt spray / corrosion test": {
        "name": "Salt Spray (Corrosion) Test", "standard": "ASTM B117 / IEC 60068-2-11",
        "description": "Determines corrosion resistance of materials and coatings by exposing components to a saline fog.",
        "procedure": [
            "Place components inside a salt spray chamber.",
            "Operate a saline (typically 5% NaCl) fog with regulated temperature (e.g., 35°C) for the specified period (e.g., 96 hours).",
            "Assess coatings and material for corrosion after cleaning the sample.",
        ],
        "equipment": ["Salt spray chamber", "Fog generator", "Temperature controllers", "Inspection microscope"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/a8dae943-cf37-4798-acea-4d96c4b558c4.png"
    },
    "dust ingress (ip rating)": {
        "name": "Dust Ingress Test (IP Ratings)", "standard": "IEC 60529",
        "description": "Evaluates resistance of an enclosure to ingress of dust particles, which is critical for achieving IP5X or IP6X ratings.",
        "procedure": [
            "Mount the DUT in a dust chamber with circulating standardized test dust (e.g., talcum powder).",
            "For IP6X, apply a vacuum inside the DUT to create a pressure difference, forcing dust to challenge seals for a prescribed duration (e.g., 8 hours).",
            "Disassemble and inspect for any internal dust contamination. No dust is permitted for an IP6X rating."
        ],
        "equipment": ["Dust test chamber", "Vacuum pump", "Standardized test dust", "Flow meter", "Inspection tools"],
        "image_url": ""
    },
    "drop test / mechanical shock": {
        "name": "Drop Test / Mechanical Shock", "standard": "IEC 60068-2-27 (Shock) / IEC 60068-2-31 (Drop)",
        "description": "Simulates mechanical shock from impacts or falls during handling or operation to evaluate structural integrity.",
        "procedure": [
            "Subject the DUT to a specified number of shocks with a defined pulse shape (e.g., half-sine), peak acceleration (G's), and duration.",
            "For drop tests, release the DUT from a defined height onto a specified surface at various orientations.",
            "Inspect for mechanical damage (cracks, deformation) and verify full electrical function."
        ],
        "equipment": ["Shock or Drop Tester", "Accelerometers", "High-speed cameras", "Data Acquisition System"],
        "image_url": ""
    },
    "overvoltage protection test": {
        "name": "Overvoltage Protection Test", "standard": "IEC 61000-4-5 / ISO 16750-2",
        "description": "Verifies component resilience to transient overvoltage events (surges).",
        "procedure": [
            "Apply standardized surge voltage waveforms to the DUT's power input using a surge generator.",
            "Monitor the voltage and current to observe the behavior of the protection circuitry (e.g., TVS diode clamping).",
            "Confirm that the device survives the surge without permanent damage and continues to function correctly."
        ],
        "equipment": ["Surge Generator", "Coupling/Decoupling Network (CDN)", "Oscilloscope"],
        "image_url": ""
    },
    "overcurrent protection test": {
        "name": "Overcurrent Protection Test", "standard": "UL 248 / IEC 60947",
        "description": "Assesses the effectiveness of internal current limiting devices under fault conditions.",
        "procedure": [
            "Create a controlled overcurrent condition by connecting a high-power electronic load or a direct short circuit.",
            "Measure the time it takes for the protection device to trip (interrupt the circuit).",
            "Verify that the protection action prevents damage and that case temperatures remain safe."
        ],
        "equipment": ["High-Current Power Supply", "DC Electronic Load", "Oscilloscope with Current Probe", "Thermal Camera"],
        "image_url": ""
    },
    "insulation resistance test": {
        "name": "Insulation Resistance Test", "standard": "IEC 60664-1",
        "description": "Measures the total resistance between any two points separated by electrical insulation to ensure its integrity.",
        "procedure": [
            "Apply a high, stable DC voltage (e.g., 500V or 1000V) across the insulation barrier being tested for 60 seconds.",
            "Measure the resulting leakage current and calculate the resistance (R = V/I).",
            "The measured resistance must exceed a minimum threshold specified by the safety standard (e.g., 10 MΩ)."
        ],
        "equipment": ["Megohmmeter (Insulation Resistance Tester)", "High Voltage Probes"],
        "image_url": ""
    },
    "dielectric strength test": {
        "name": "Dielectric Strength Test (Hipot)", "standard": "IEC 60243 / IEC 60664-1",
        "description": "Determines if the insulation of a component can withstand high voltage transients without breaking down.",
        "procedure": [
            "Apply a high AC or DC voltage (e.g., 1.5 kV AC) to the insulation barrier for 60 seconds.",
            "Monitor the leakage current. A sudden spike in current indicates a dielectric breakdown (failure).",
            "The leakage current must not exceed a predefined limit."
        ],
        "equipment": ["Hipot Tester (Dielectric Analyzer)", "High Voltage Test Leads", "Safety Enclosure"],
        "image_url": ""
    },
    "electrostatic discharge (esd) test": {
        "name": "Electrostatic Discharge (ESD) Test", "standard": "IEC 61000-4-2",
        "description": "Evaluates immunity to static electricity discharges from human contact or other sources.",
        "procedure": [
            "Use a calibrated ESD gun to apply 'contact' and 'air' discharges to specified points.",
            "Apply a specified number of positive and negative polarity discharges at several voltage levels (e.g., ±2kV, ±4kV, ±8kV).",
            "Monitor the device for any disruption in operation, such as resets, data corruption, or permanent damage."
        ],
        "equipment": ["ESD Simulator (ESD Gun)", "Horizontal and Vertical Coupling Planes", "Ground Reference Plane"],
        "image_url": "https://user-gen-media-assets.s3.amazonaws.com/seedream_images/4a0a4660-b90e-4429-994e-9abb6b82feb9.png"
    },
    "emi/emc test": {
        "name": "EMI/EMC Test (Electromagnetic Compatibility)", "standard": "CISPR 25, IEC 61000 series",
        "description": "Verifies that the device doesn’t emit excessive interference and can tolerate external interference.",
        "procedure": [
            "This is a comprehensive suite of tests that includes:",
            "1. Radiated Emissions: Measuring RF noise radiated from the device.",
            "2. Conducted Emissions: Measuring RF noise conducted onto its cables.",
            "3. Radiated Immunity: Testing tolerance to external RF fields.",
            "4. Conducted Immunity: Testing tolerance to RF noise injected onto its cables."
        ],
        "equipment": ["EMI Receiver", "Anechoic Chamber", "Signal Generators", "RF Amplifiers", "Antennas", "LISN"],
        "image_url": ""
    },
    "conducted immunity test": {
        "name": "Conducted Immunity Test", "standard": "IEC 61000-4-6",
        "description": "Assesses a device's tolerance to conducted radio-frequency (RF) disturbances on its power or signal lines.",
        "procedure": [
            "Inject amplitude-modulated RF signals from a generator onto the DUT's cables using a coupling/decoupling network (CDN) or a bulk current injection (BCI) probe.",
            "Sweep the test across a specified frequency range (e.g., 150 kHz to 80 MHz).",
            "Monitor the DUT for any signs of performance degradation or malfunction during the injection."
        ],
        "equipment": ["RF Signal Generator", "RF Amplifier", "Coupling/Decoupling Network (CDN)"],
        "image_url": ""
    },
    "radiated emissions test": {
        "name": "Radiated Emissions Test", "standard": "CISPR 25",
        "description": "Measures the level of unintentional electromagnetic energy radiated from a device and its wiring harness.",
        "procedure": [
            "Place the device and its harness in a semi-anechoic chamber on a non-conductive table.",
            "Power up the device in its typical operating mode.",
            "Use a calibrated antenna to scan for RF emissions across the specified frequency range (e.g., 150 kHz to 2.5 GHz).",
            "Compare the measured emissions to the regulatory limits."
        ],
        "equipment": ["Anechoic Chamber", "Calibrated Antennas", "EMI Receiver or Spectrum Analyzer"],
        "image_url": ""
    },
    "endurance / life cycle test": {
        "name": "Endurance / Life Cycle Test", "standard": "AEC-Q100/AEC-Q200",
        "description": "Simulates the expected operational lifetime stresses on a component to identify potential wear-out mechanisms and verify long-term reliability.",
        "procedure": [
            "Subject the device to a large number of operational cycles (e.g., power on/off, thermal cycles, full load/no load) in an environmental chamber.",
            "Run these tests over an accelerated timeline to simulate years of field use.",
            "Analyze any failures to understand the root cause (e.g., material fatigue, component drift)."
        ],
        "equipment": ["Environmental Chamber", "Power Cycling Equipment", "Data Loggers", "Programmable Loads"],
        "image_url": ""
    },
    "connector durability test": {
        "name": "Connector Durability Test", "standard": "IEC 60512",
        "description": "Evaluates the mechanical and electrical performance of connectors over repeated mating cycles.",
        "procedure": [
            "Perform a specified number of mating and unmating cycles on the connector pair, often using an automated machine.",
            "Measure the low-level contact resistance (LLCR) before, during, and after the cycling.",
            "Inspect the connector contacts for wear, plating degradation, and mechanical deformation using a microscope."
        ],
        "equipment": ["Connector Cycling Machine", "Contact Resistance Meter", "Inspection Microscope"],
        "image_url": ""
    }
}

# --- FULLY RESTORED COMPONENT DATABASE ---
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
    "c1210c226k8racauto": {"Manufacturer": "KEMET", "Product Category": "Capacitor", "RoHS": "Yes", "Capacitance": "22uF", "Voltage Rating DC": "10V", "Dielectric": "X7R", "Case Code - in": "1210", "Tolerance": "10%", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "125 C", "Qualification": "AEC-Q200"},
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
    "mmbz5227blt3g": {"Manufacturer": "onsemi", "Product Category": "Zener Diode", "RoHS": "Yes", "Vz": "3.6V", "Power": "225mW", "Tolerance": "5%", "Package": "SOT-23", "Minimum Operating Temperature": "-55 C", "Maximum Operating Temperature": "150 C"},
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
    "ac0603fr-074k7l": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "4.7 kOhm", "Power": "0.1W", "Tolerance": "1%", "Case Code - in": "0603", "Qualification": "AEC-Q200"},
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
    "rc0402fr-071m0l": {"Manufacturer": "Yageo", "Product Category": "Resistor", "RoHS": "Yes", "Resistance": "1 MOhm", "Power": "0.063W", "Tolerance": "1%", "Case Code - in": "0402", "Qualification": "AEC-Q200"},
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
    "ncp164csnadjt1g": {"Manufacturer": "onsemi", "Product Category": "LDO Voltage Regulators", "RoHS": "Yes", "Mounting Style": "SMD/SMT", "Package/Case": "TSOP-5", "Output Current": "300 mA", "Number of Outputs": "1 Output", "Polarity": "Positive", "Quiescent Current": "30 uA", "Input Voltage - Min": "1.6 V", "Input Voltage - Max": "5.5 V", "PSRR / Ripple Rejection - Typ": "85 dB", "Output Type": "Adjustable", "Minimum Operating Temperature": "-40 C", "Maximum Operating Temperature": "+150 C", "Series": "NCP164C", "Packaging": "Reel", "Brand": "onsemi", "Line Regulation": "0.5 mV/V", "Load Regulation": "2 mV/V", "Operating Temperature Range": "-40 C to +150 C", "Output Voltage Range": "1.2 V to 4.5 V", "Product": "LDO Voltage Regulators", "Product Type": "LDO Voltage Regulators", "Subcategory": "PMIC - Power Management ICs", "Type": "Low Noise", "Voltage Regulation Accuracy": "2 %"},
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
            r'^(.*?)\s*-->\s*(Passed|Failed|Success)\s*-->\s*(.+)$', r'^(.*?)\s*-->\s*(.+)$',
            r'^\d+:\s*([A-Z_]+):\s*\"([A-Z]+)\"$', r'^(.+?)\s+is\s+(success|failure|passed|failed)$',
            r'^(.+?)\s+(Failed|Passed)$',
        ]
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
                KEYWORD_TO_STANDARD_MAP = {"gps": "NMEA 0183", "can": "ISO 11898", "vibration": "IEC 60068-2-6"}
                for keyword, standard in KEYWORD_TO_STANDARD_MAP.items():
                    if keyword in test_data["TestName"].lower():
                        test_data["Standard"] = standard
                        break
                extracted_tests.append(test_data)
                break
    return extracted_tests

def parse_report(uploaded_file):
    if not uploaded_file: return []
    try:
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

# --- Component Information Module (FINAL - ROYAL LOOK) ---
if option == "Component Information":
    st.subheader("Key Component Information", anchor=False)
    st.caption("Look up parts from the component database.")
    part_q = st.text_input("Quick Lookup (part number)", placeholder="e.g., ncp164csnadjt1g").lower().strip()
    if st.button("Find Component"):
        if part_q:
            result = UNIFIED_COMPONENT_DB.get(part_q)
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
        st.markdown("---")
        data_items = list(component.items())
        col1, col2 = st.columns(2)
        midpoint = (len(data_items) + 1) // 2
        with col1:
            for i, (key, value) in enumerate(data_items[:midpoint]):
                st.markdown(f"<div class='attr-item'><span>{i+1}. </span><strong>{key.replace('_', ' ').title()}:</strong> {str(value)}</div>", unsafe_allow_html=True)
        with col2:
            for i, (key, value) in enumerate(data_items[midpoint:], start=midpoint):
                st.markdown(f"<div class='attr-item'><span>{i+1}. </span><strong>{key.replace('_', ' ').title()}:</strong> {str(value)}</div>", unsafe_allow_html=True)

# --- Test Requirement Generation Module (FINAL - WITH IMAGES) ---
elif option == "Test Requirement Generation":
    st.subheader("Generate Detailed Test Requirements", anchor=False)
    st.caption("Enter keywords to generate detailed automotive test procedures.")
    text_input = st.text_input("Enter a test case keyword", placeholder="Try: 'vibration', 'esd', 'salt spray'...")
    if st.button("Generate Requirements"):
        user_case = text_input.strip().lower()
        if user_case:
            matched_test = None
            for key, test_data in TEST_CASE_KNOWLEDGE_BASE.items():
                if user_case in key.lower():
                    matched_test = test_data
                    break
            if matched_test:
                st.markdown(f"#### Generated Procedure for: **{matched_test.get('name', 'N/A')}**")
                with st.container():
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    if matched_test.get("image_url"):
                        st.image(matched_test["image_url"], caption=f"Test Setup for {matched_test.get('name')}")
                    st.markdown(f"**Standard:** {matched_test.get('standard', 'N/A')}")
                    st.markdown(f"**Description:** {matched_test.get('description', 'N/A')}")
                    st.markdown("**Test Procedure:**")
                    for step in matched_test.get('procedure', []): st.markdown(f"- {step}")
                    st.markdown("**Required Equipment:**")
                    for item in matched_test.get('equipment', []): st.markdown(f"- {item}")
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning(f"No detailed procedure found for '{user_case}'.")

# --- Test Report Verification Module (RESTORED) ---
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
            st.warning("No recognizable data was extracted from the uploaded file.")

# --- Dashboard & Analytics Module ---
elif option == "Dashboard & Analytics":
    st.subheader("Dashboard & Analytics", anchor=False)
    st.caption("High-level view of session activities.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports Verified", st.session_state.get("reports_verified", 0))
    c2.metric("Requirements Generated", st.session_state.get("requirements_generated", 0))
    c3.metric("Components in DB", len(UNIFIED_COMPONENT_DB))
