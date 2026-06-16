import argparse
import sys
import os
import json
from datetime import datetime
from streamlit.web import cli as stcli
from satlinksim.infrastructure.api.client import SatLinkSimClient
from satlinksim.infrastructure.api.schemas import SimulationRequest, GroundStation, ItuRain
from satlinksim.ground_stations import GROUND_STATIONS

def run_ui():
    app_path = os.path.join(os.path.dirname(__file__), "infrastructure", "ui", "streamlit_app.py")
    sys.argv = ["streamlit", "run", app_path]
    sys.exit(stcli.main())

def main_ui():
    run_ui()

def run_api():
    from satlinksim.infrastructure.api.server import main as start_server
    start_server()

def run_simulate(args):
    client = SatLinkSimClient(base_url=args.url)
    
    # Filter ground stations if names provided
    gs_to_sim = []
    if args.stations:
        names = args.stations.split(",")
        gs_to_sim = [gs for gs in GROUND_STATIONS if gs["name"] in names]
    else:
        gs_to_sim = GROUND_STATIONS
        
    if not gs_to_sim:
        print("No matching ground stations found.")
        return

    # Prepare request
    gs_models = []
    for gs in gs_to_sim:
        itu = ItuRain(**gs["itu_rain"])
        gs_models.append(GroundStation(
            name=gs["name"],
            eirp_dbw=gs["eirp_dbw"],
            g_rx_dbi=gs["g_rx_dbi"],
            system_temp_k=gs["system_temp_k"],
            antenna_diam_m=gs["antenna_diam_m"],
            latitude=gs["latitude"],
            longitude=gs["longitude"],
            altitude_km=gs["altitude_km"],
            itu_rain=itu,
            wv_g_m3=gs["wv_g_m3"],
            humidity_pct=gs["humidity_pct"],
            v_radial_ms=gs["v_radial_ms"],
            norad_id=gs.get("norad_id"),
            sat_name=gs.get("sat_name"),
            sat_lon_deg=gs.get("sat_lon_deg")
        ))

    request = SimulationRequest(
        ground_stations=gs_models,
        n_steps=args.steps,
        dt_s=args.dt,
        freq_hz=args.freq,
        bandwidth_hz=args.bw,
        force_rain=args.force_rain
    )

    print(f"Sending simulation request to {args.url}...")
    try:
        response = client.simulate(request)
        print(f"Received results for {len(response.results)} stations.")
        
        for res in response.results:
            print(f"\nStation: {res.name}")
            print(f"  Mean SNR: {res.snr_mean:.2f} dB")
            print(f"  Outage Fraction: {res.outage_fraction*100:.2f}%")
            print(f"  Handoffs: {len(res.handoff_events)}")
            
        if args.output:
            with open(args.output, "w") as f:
                f.write(response.model_dump_json())
            print(f"\nFull results saved to {args.output}")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="SatLinkSim CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # UI command
    ui_parser = subparsers.add_parser("ui", help="Run the Streamlit UI")

    # API command
    api_parser = subparsers.add_parser("api", help="Run the FastAPI server")

    # Simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run simulation via REST API")
    sim_parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    sim_parser.add_argument("--stations", help="Comma-separated station names")
    sim_parser.add_argument("--steps", type=int, default=3600, help="Number of steps")
    sim_parser.add_argument("--dt", type=float, default=1.0, help="Time step in seconds")
    sim_parser.add_argument("--freq", type=float, default=14e9, help="Carrier frequency in Hz")
    sim_parser.add_argument("--bw", type=float, default=36e6, help="Bandwidth in Hz")
    sim_parser.add_argument("--force-rain", action="store_true", help="Force rain generation")
    sim_parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    if args.command == "ui":
        run_ui()
    elif args.command == "api":
        run_api()
    elif args.command == "simulate":
        run_simulate(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
