"""Build a small source-checked PowerFlex 525 diagnostic set.

The cards paraphrase fault descriptions/actions from Rockwell's 2016 On Drive
Guide. Questions are constructed diagnostic scenarios, not field incidents.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "industrial_pf525"
SOURCE = "https://literature.rockwellautomation.com/idc/groups/literature/documents/du/520-du001_-en-e.pdf"

# group, broad symptom, fault A, action A, description A, fault B, action B, description B
PAIRS = [
    ("supply_voltage", "a supply-voltage fault", ("F004", "CHECK_LOW_LINE", "DC bus undervoltage: inspect incoming AC line for low voltage or interruption.", 4), ("F005", "CHECK_HIGH_LINE_REGEN", "DC bus overvoltage: inspect high line voltage or transients and consider motor regeneration and deceleration time.", 4)),
    ("temperature", "an over-temperature fault", ("F008", "CHECK_HEATSINK_COOLING", "Heatsink or power-module over-temperature: inspect heatsink blockage, rated ambient temperature, and fan.", 5), ("F009", "CHECK_CONTROL_COOLING", "Control-module over-temperature: inspect ambient temperature, airflow obstruction, debris, and fan.", 5)),
    ("motor_load", "a motor acceleration or overload fault", ("F006", "CHECK_STALL_ACCEL_LOAD", "Motor stall during acceleration or deceleration: inspect load and acceleration time/current-limit settings.", 4), ("F007", "CHECK_MOTOR_OVERLOAD", "Motor electronic overload: inspect excess load relative to P033 Motor OL Current and A530 Boost Select.", 4)),
    ("signal_loss", "a signal-loss fault", ("F021", "CHECK_OUTPUT_PHASE", "Output phase loss when that protection is enabled: verify motor wiring and motor; A557 controls the feature.", 5), ("F029", "CHECK_ANALOG_INPUT", "Analog input loss where configured to fault: inspect input connections and t094/t097 signal-loss parameters.", 5)),
    ("power_or_overload", "a power or drive-overload fault", ("F003", "CHECK_POWER_FUSES_LOAD", "Power loss associated with single-phase operation and load: inspect incoming line, input fuses, and load.", 4), ("F064", "CHECK_DRIVE_OVERLOAD", "Drive overload rating exceeded: inspect load and acceleration time.", 5)),
    ("network_control_a", "a network-control interruption", ("F071", "CHECK_DSI_NETWORK", "Modbus or DSI network control interrupted: inspect communications cabling, Modbus/DSI settings and status.", 5), ("F072", "CHECK_OPTION_NETWORK", "Network option card remote control interrupted: inspect cabling, adapter settings, and external network status.", 5)),
    ("network_control_b", "a network-control interruption", ("F073", "CHECK_EMBEDDED_ETHERNET", "Embedded EtherNet/IP control interrupted: inspect cabling, EtherNet/IP settings, and external network status.", 5), ("F081", "CHECK_DSI_MASTER_COMM", "Communication with Modbus or DSI master interrupted: inspect cabling, settings, status, and C125 Comm Loss Action.", 6)),
    ("network_internal", "an internal communication fault", ("F082", "CHECK_OPTION_CARD_LINK", "Drive-to-network-option-card communication lost: inspect/reseat the option card and C125 Comm Loss Action.", 6), ("F083", "CHECK_EMBEDDED_ADAPTER_LINK", "Internal communication with embedded EtherNet/IP adapter lost: inspect Ethernet settings, diagnostic parameters, and C125.", 6)),
    ("safety", "a safety-input related fault", ("F059", "CHECK_SAFETY_INPUT_STATUS", "Safety Open: both safety inputs are not enabled; inspect safety input signals and t105 configuration.", 5), ("F111", "CHECK_SAFETY_HARDWARE", "Safety input hardware malfunction: inspect safety signals; if fault persists, service the control module.", 6)),
    ("control_power_module", "a control/power-module compatibility fault", ("F106", "CHECK_025HP_INCOMPATIBILITY", "PowerFlex 525 control module does not support a 0.25 HP power module; check module compatibility, with a compatible power module or PowerFlex 523 control module as documented options.", 6), ("F107", "CHECK_UNRECOGNIZED_MODULE", "Control module cannot recognize the power module: check power module, then control module if the fault persists.", 6)),
    ("firmware", "a firmware-related fault", ("F125", "CHECK_FIRMWARE_FLASH", "Firmware corrupt, mismatched, or hardware-incompatible: attempt a valid firmware flash update.", 6), ("F127", "CHECK_DSI_FIRMWARE_FLASH", "Critical firmware fault with DSI-only backup firmware: attempt a valid firmware flash update through DSI communications.", 6)),
    ("mechanical_load", "a motor/load-connection fault", ("F015", "CHECK_LOAD_LOSS", "Load-loss threshold/time met: inspect motor-to-load connection and A490/A491 settings.", 5), ("F063", "CHECK_SHEAR_PIN_LIMIT", "Software shear-pin threshold/time met: inspect motor-to-load connection and A486-A489 settings.", 5)),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cards, cases = [], []
    for number, (group, symptom, left, right) in enumerate(PAIRS, 1):
        split = "dev" if number <= 8 else "test"
        for side, item in (("a", left), ("b", right)):
            code, action_id, description, page = item
            cards.append({
                "id": f"pf525-{code.lower()}", "title": f"PowerFlex 525 fault {code}",
                "text": f"Applicable model: PowerFlex 525. Displayed fault: {code}. {description} Diagnostic action ID: {action_id}.",
                "metadata": {"model": "PowerFlex 525", "fault_code": code, "action_id": action_id,
                             "source_url": SOURCE, "source_page": page, "source_publication": "520-DU001D-EN-E, April 2016"},
            })
            cases.append({
                "id": f"{group}-{side}", "pair_group": group, "split": split,
                "question": f"A PowerFlex 525 drive reports {symptom}. The displayed fault code is {code}. Which diagnostic check is supported by the guide?",
                "observed_state": {"model": "PowerFlex 525", "fault_code": code},
                "gold_decision": action_id, "gold_evidence_ids": [f"pf525-{code.lower()}"],
                "needs_clarification": False, "scenario_origin": "constructed from source-checked fault row",
            })
        cases.append({
            "id": f"{group}-missing", "pair_group": group, "split": split,
            "question": f"A PowerFlex 525 drive reports {symptom}, but the displayed fault code was not recorded. Which diagnostic check is supported by the guide?",
            "observed_state": {"model": "PowerFlex 525", "fault_code": None},
            "gold_decision": "ASK_FAULT_CODE", "gold_evidence_ids": [f"pf525-{left[0].lower()}", f"pf525-{right[0].lower()}"],
            "needs_clarification": True, "clarification_field": "fault_code",
            "scenario_origin": "constructed missing-field variant; not a field incident",
        })
    assert len(cards) == 24 and len(cases) == 36
    assert len({x["id"] for x in cards}) == len(cards)
    assert len({x["id"] for x in cases}) == len(cases)
    ids = {x["id"] for x in cards}
    assert all(set(c["gold_evidence_ids"]) <= ids for c in cases)
    for name, value in (("corpus.json", cards), ("cases.json", cases)):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    manifest = {
        "description": "Source-checked constructed diagnostic set; no expert field validation",
        "source_url": SOURCE, "source_publication": "520-DU001D-EN-E, April 2016",
        "model_scope": "PowerFlex 525 only", "firmware_version_scope": "No firmware-specific applicability claim",
        "cards": len(cards), "cases": len(cases), "dev_cases": sum(c["split"] == "dev" for c in cases),
        "test_cases": sum(c["split"] == "test" for c in cases),
        "sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in ("corpus.json", "cases.json")},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"cards": len(cards), "cases": len(cases), "dev": manifest["dev_cases"], "test": manifest["test_cases"]}))


if __name__ == "__main__":
    main()
