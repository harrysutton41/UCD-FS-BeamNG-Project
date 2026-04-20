import time
import numpy as np
from beamngpy import BeamNGpy, Scenario, Vehicle, set_up_simple_logging

BEAMNG_HOME = r"C:\Users\Admin\Desktop\BeamNG.tech.v0.37.6.0"
USER_HOME   = r"C:\Users\Admin\AppData\Local\BeamNG\BeamNG.tech"

REF_PATH_FILE = "ref_path.npz"

WAYPOINTS = [
    'DR43_2', 'DR55_37', 'DR48_3', 'DR46_4',
    'DR50_4', 'DR1_61', 'DR55_37', 'DR9_16', 'DR43_2'
]

POLL_INTERVAL = 0.05
MAX_RUNTIME   = 180
MIN_MOVE_DIST = 0.25   # only save a new point if car moved at least this far


def cumulative_s(x, y, z):
    pts = np.column_stack((x, y, z))
    ds = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate(([0.0], np.cumsum(ds)))
    return s


def main():
    set_up_simple_logging()

    bng = BeamNGpy("localhost", 25252, home=BEAMNG_HOME, user=USER_HOME)
    bng.open(launch=True)

    vehicle = Vehicle(
        "ego_vehicle",
        model="test1",
        licence="REFRUN",
        color="Blue",
        part_config="vehicles/test1/cfg_000.pc"
    )

    scenario = Scenario("driver_training", "Reference_Path_Recorder")
    scenario.add_vehicle(vehicle, pos=(-206, 311, 53.093), rot_quat=(0, 0, 0, 0.96))
    scenario.make(bng)

    bng.settings.set_deterministic(60)
    bng.scenario.load(scenario)
    bng.ui.hide_hud()
    bng.scenario.start()

    print("Waiting for vehicle to settle...")
    time.sleep(2.0)

    print("Starting AI waypoint run to record reference path...")
    print("Press Ctrl+C when you want to stop and save the path.")
    vehicle.ai.drive_using_waypoints(
        WAYPOINTS,
        drive_in_lane=False,
        avoid_cars=False,
        no_of_laps=1,
        route_speed=100.0 / 3.6,
        route_speed_mode='limit',
        aggression=0.75
    )

    x_data, y_data, z_data = [], [], []

    start_time = time.time()
    last_saved = None
    samples = 0

    try:
        while True:
            if time.time() - start_time > MAX_RUNTIME:
                print("Stopped by safety timeout.")
                break

            vehicle.sensors.poll()
            state = vehicle.sensors["state"]
            pos = np.array(state["pos"], dtype=float)

            if last_saved is None:
                x_data.append(pos[0])
                y_data.append(pos[1])
                z_data.append(pos[2])
                last_saved = pos.copy()
                samples += 1
            else:
                moved = np.linalg.norm(pos - last_saved)
                if moved >= MIN_MOVE_DIST:
                    x_data.append(pos[0])
                    y_data.append(pos[1])
                    z_data.append(pos[2])
                    last_saved = pos.copy()
                    samples += 1

            if samples % 50 == 0 and samples > 0:
                print(f"Recorded {samples} reference points...")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopped by user. Saving reference path...")

    finally:
        if len(x_data) < 2:
            print("Not enough points recorded to create a reference path.")
        else:
            x = np.array(x_data)
            y = np.array(y_data)
            z = np.array(z_data)
            s = cumulative_s(x, y, z)

            np.savez(REF_PATH_FILE, x=x, y=y, z=z, s=s)

            print(f"\nSaved reference path to: {REF_PATH_FILE}")
            print(f"Points saved: {len(x)}")
            print(f"Total path length: {s[-1]:.2f} m")

        bng.ui.show_hud()
        bng.disconnect()


if __name__ == "__main__":
    main()
